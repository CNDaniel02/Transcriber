from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.models import PipelineOptions
from src.service import TranscriptService


LOGGER = logging.getLogger("transcribe_pipeline")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video with Whisper large-v3 (single file or batch directory)."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="Path to input audio/video file")
    input_group.add_argument("--input-dir", help="Path to input directory for batch processing")

    parser.add_argument("--output-dir", default="output", help="Directory for transcript txt")
    parser.add_argument("--temp-dir", default="temp", help="Directory for temp wav files")
    parser.add_argument("--models-dir", default="models", help="Whisper model cache directory")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan input directory")
    parser.add_argument(
        "--output-name",
        default=None,
        help="Output file name for single-file mode",
    )
    parser.add_argument("--model", default="large-v3", help="Whisper model name")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="Inference device")
    parser.add_argument("--precision", default="fp32", choices=["fp32", "fp16"], help="Inference precision")
    parser.add_argument("--language", default=None, help="Language hint, for example zh or en")
    parser.add_argument(
        "--pause-threshold",
        type=float,
        default=1.2,
        help="Seconds of silence gap to switch speaker label",
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        default=2,
        help="Max number of rotating speaker labels",
    )

    parser.set_defaults(include_timestamps=False, include_speakers=False)
    parser.add_argument(
        "--include-timestamps",
        action="store_true",
        dest="include_timestamps",
        help="Include timestamps in transcript output",
    )
    parser.add_argument(
        "--no-timestamps",
        action="store_false",
        dest="include_timestamps",
        help="Do not include timestamps in transcript output",
    )
    parser.add_argument(
        "--include-speakers",
        action="store_true",
        dest="include_speakers",
        help="Include basic speaker labels in transcript output",
    )
    parser.add_argument(
        "--no-speakers",
        action="store_false",
        dest="include_speakers",
        help="Do not include speaker labels in transcript output",
    )

    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="FFmpeg binary name or full path")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary wav files")
    parser.add_argument(
        "--output-conflict-strategy",
        default="timestamp",
        choices=["timestamp", "sequence", "overwrite"],
        help="How to handle existing output filename conflicts",
    )
    parser.add_argument("--log-level", default="INFO", help="Log level, for example INFO or DEBUG")
    return parser


def configure_logging(log_level: str) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "pipeline.log"

    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def run_pipeline(args: argparse.Namespace) -> int:
    options = PipelineOptions(
        model_name=args.model,
        device=args.device,
        precision=args.precision,
        language=args.language,
        include_timestamps=args.include_timestamps,
        include_speakers=args.include_speakers,
        pause_threshold_sec=args.pause_threshold,
        max_speakers=max(1, args.max_speakers),
        ffmpeg_bin=args.ffmpeg_bin,
        keep_temp_files=args.keep_temp,
        output_conflict_strategy=args.output_conflict_strategy,
    )

    service = TranscriptService(
        options=options,
        temp_dir=Path(args.temp_dir),
        models_dir=Path(args.models_dir),
        logger=LOGGER,
    )

    if args.input:
        result = service.transcribe_file(
            input_file=args.input,
            output_dir=args.output_dir,
            output_name=args.output_name,
        )
        LOGGER.info("Transcript written to: %s", result.output_file)
        return 0

    batch_result = service.transcribe_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        recursive=args.recursive,
    )
    LOGGER.info(
        "Batch complete. total=%s success=%s failed=%s",
        batch_result.total_files,
        batch_result.success_files,
        batch_result.failed_files,
    )
    for output in batch_result.outputs:
        LOGGER.info("Output: %s", output)
    for error in batch_result.errors:
        LOGGER.error("Batch error: %s", error)

    return 0 if batch_result.failed_files == 0 else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    try:
        return run_pipeline(args)
    except Exception:
        LOGGER.exception("Pipeline failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
