from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from src.format_txt import write_transcript_txt
from src.input_router import list_supported_media_files, resolve_input
from src.media_preprocess import cleanup_temp_file, convert_to_wav, ensure_ffmpeg_available
from src.models import BatchTranscriptionResult, FileTranscriptionResult, PipelineOptions
from src.progress import NullProgressCallback, ProgressCallback
from src.speaker_rules import assign_speakers
from src.transcribe_whisper import TranscribeConfig, WhisperTranscriber


class TranscriptService:
    _transcribe_lock = threading.Lock()

    def __init__(
        self,
        options: PipelineOptions,
        temp_dir: Path | str = "temp",
        models_dir: Path | str = "models",
        logger: logging.Logger | None = None,
    ) -> None:
        options.validate()
        self.options = options
        self.temp_dir = Path(temp_dir).resolve()
        self.models_dir = Path(models_dir).resolve()
        self.logger = logger or logging.getLogger("transcribe_service")

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.ffmpeg_bin = self._resolve_ffmpeg_bin(options.ffmpeg_bin)
        ensure_ffmpeg_available(ffmpeg_bin=self.ffmpeg_bin)
        self._ensure_ffmpeg_on_path(self.ffmpeg_bin)

        transcribe_config = TranscribeConfig(
            model_name=self.options.model_name,
            requested_device=self.options.device,
            precision=self.options.precision,
            language=self.options.language,
        )
        self.transcriber = WhisperTranscriber(
            config=transcribe_config,
            cache_dir=self.models_dir,
            logger=self.logger,
        )

    def _resolve_ffmpeg_bin(self, requested_bin: str) -> str:
        requested = Path(requested_bin)
        if requested.is_file():
            return str(requested.resolve())

        if requested_bin != "ffmpeg":
            raise RuntimeError(f"FFmpeg binary path does not exist: {requested_bin}")

        on_path = shutil.which("ffmpeg")
        if on_path:
            return on_path

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            winget_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_root.exists():
                candidates = [
                    path
                    for path in winget_root.rglob("ffmpeg.exe")
                    if "Gyan.FFmpeg" in str(path)
                ]
                if candidates:
                    candidates.sort(key=lambda item: str(item), reverse=True)
                    return str(candidates[0])

        raise RuntimeError(
            "FFmpeg not found. Install FFmpeg or pass an explicit --ffmpeg-bin path."
        )

    @staticmethod
    def _ensure_ffmpeg_on_path(ffmpeg_bin: str) -> None:
        ffmpeg_path = Path(ffmpeg_bin)
        if not ffmpeg_path.is_file():
            return

        ffmpeg_dir = str(ffmpeg_path.parent.resolve())
        current_path = os.environ.get("PATH", "")
        path_entries = current_path.split(os.pathsep) if current_path else []
        normalized_entries = {Path(entry).as_posix().lower() for entry in path_entries if entry}
        if Path(ffmpeg_dir).as_posix().lower() not in normalized_entries:
            os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}" if current_path else ffmpeg_dir

    def _resolve_output_path(self, input_file: Path, output_dir: Path, output_name: str | None) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_name:
            path = output_dir / output_name
            if path.suffix.lower() != ".txt":
                path = path.with_suffix(".txt")
        else:
            path = output_dir / f"{input_file.stem}_transcript.txt"

        if not path.exists() or self.options.output_conflict_strategy == "overwrite":
            return path

        if self.options.output_conflict_strategy == "timestamp":
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return output_dir / f"{input_file.stem}_{stamp}_transcript.txt"

        for index in range(1, 1000):
            candidate = output_dir / f"{input_file.stem}_transcript_{index:03d}.txt"
            if not candidate.exists():
                return candidate

        raise RuntimeError("Too many output name conflicts in output directory.")

    def _transcribe_single(
        self,
        input_file: Path,
        output_dir: Path,
        output_name: str | None,
        callback: ProgressCallback,
        index: int,
        total: int,
    ) -> FileTranscriptionResult:
        callback.on_file_start(index, total, input_file)
        started = time.perf_counter()
        normalized_wav: Path | None = None

        try:
            input_media = resolve_input(str(input_file))
            callback.on_info(f"Preparing media: {input_media.path.name}")
            normalized_wav = convert_to_wav(
                input_path=input_media.path,
                temp_dir=self.temp_dir,
                ffmpeg_bin=self.ffmpeg_bin,
            )

            callback.on_info("Running whisper transcription...")
            with self._transcribe_lock:
                result = self.transcriber.transcribe(normalized_wav)

            segments = result.segments
            if self.options.include_speakers:
                segments = assign_speakers(
                    segments=segments,
                    pause_threshold_sec=self.options.pause_threshold_sec,
                    max_speakers=self.options.max_speakers,
                )

            output_path = self._resolve_output_path(
                input_file=input_media.path,
                output_dir=output_dir,
                output_name=output_name,
            )

            metadata = {
                "source_file": str(input_media.path),
                "source_type": input_media.kind,
                "model": result.model_name,
                "device": result.device_used,
                "precision": self.options.precision,
                "language": result.language or "auto",
                "segments": str(len(segments)),
                "timestamps_enabled": str(self.options.include_timestamps),
                "speaker_labels_enabled": str(self.options.include_speakers),
            }
            write_transcript_txt(
                output_path=output_path,
                metadata=metadata,
                segments=segments,
                include_timestamps=self.options.include_timestamps,
                include_speakers=self.options.include_speakers,
            )

            elapsed = time.perf_counter() - started
            callback.on_file_done(index, total, input_media.path, output_path)
            return FileTranscriptionResult(
                input_file=input_media.path,
                output_file=output_path,
                device_used=result.device_used,
                language=result.language or "auto",
                segment_count=len(segments),
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            callback.on_error(index, total, input_file, str(exc))
            raise
        finally:
            if normalized_wav and not self.options.keep_temp_files:
                cleanup_temp_file(normalized_wav)

    def transcribe_file(
        self,
        input_file: Path | str,
        output_dir: Path | str = "output",
        output_name: str | None = None,
        callback: ProgressCallback | None = None,
    ) -> FileTranscriptionResult:
        progress = callback or NullProgressCallback()
        output_dir_path = Path(output_dir).expanduser().resolve()
        output_dir_path.mkdir(parents=True, exist_ok=True)

        file_path = Path(input_file).expanduser().resolve()
        result = self._transcribe_single(
            input_file=file_path,
            output_dir=output_dir_path,
            output_name=output_name,
            callback=progress,
            index=1,
            total=1,
        )
        progress.on_complete(total=1, success=1, failed=0)
        return result

    def transcribe_directory(
        self,
        input_dir: Path | str,
        output_dir: Path | str = "output",
        recursive: bool = False,
        callback: ProgressCallback | None = None,
    ) -> BatchTranscriptionResult:
        progress = callback or NullProgressCallback()
        input_dir_path = Path(input_dir).expanduser().resolve()
        output_dir_path = Path(output_dir).expanduser().resolve()
        output_dir_path.mkdir(parents=True, exist_ok=True)

        files = list_supported_media_files(input_dir_path, recursive=recursive)
        if not files:
            raise ValueError(f"No supported media files found in directory: {input_dir_path}")

        summary = BatchTranscriptionResult(total_files=len(files))
        progress.on_batch_start(total_files=len(files))

        for index, input_file in enumerate(files, start=1):
            try:
                file_result = self._transcribe_single(
                    input_file=input_file,
                    output_dir=output_dir_path,
                    output_name=None,
                    callback=progress,
                    index=index,
                    total=len(files),
                )
                summary.success_files += 1
                summary.outputs.append(file_result.output_file)
            except Exception as exc:
                summary.failed_files += 1
                summary.errors.append(f"{input_file}: {exc}")

        progress.on_complete(
            total=summary.total_files,
            success=summary.success_files,
            failed=summary.failed_files,
        )
        return summary
