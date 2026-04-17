from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path


def _decode_output(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").strip()


def ensure_ffmpeg_available(ffmpeg_bin: str = "ffmpeg") -> None:
    try:
        subprocess.run(
            [ffmpeg_bin, "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "FFmpeg is not available. Install FFmpeg and add it to PATH, or pass --ffmpeg-bin."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = _decode_output(exc.stderr or b"")
        raise RuntimeError(f"FFmpeg check failed: {stderr}") from exc


def convert_to_wav(input_path: Path, temp_dir: Path, ffmpeg_bin: str = "ffmpeg") -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_wav = temp_dir / f"{input_path.stem}_{timestamp}_16k_mono.wav"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_wav),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        stderr = _decode_output(exc.stderr or b"")
        raise RuntimeError(f"FFmpeg conversion failed: {stderr}") from exc

    return output_wav


def cleanup_temp_file(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink(missing_ok=True)
