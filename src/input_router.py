from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".aac",
    ".ogg",
    ".wma",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".flv",
    ".wmv",
}

SUPPORTED_MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


@dataclass(frozen=True)
class InputMedia:
    path: Path
    kind: str


def resolve_input(input_path: str) -> InputMedia:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path must be a file: {path}")

    suffix = path.suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return InputMedia(path=path, kind="audio")
    if suffix in VIDEO_EXTENSIONS:
        return InputMedia(path=path, kind="video")

    supported = ", ".join(sorted(SUPPORTED_MEDIA_EXTENSIONS))
    raise ValueError(f"Unsupported media extension: {suffix}. Supported: {supported}")


def list_supported_media_files(directory: Path, recursive: bool = False) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Input directory not found: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Input path must be a directory: {directory}")

    pattern = "**/*" if recursive else "*"
    files = [
        path.resolve()
        for path in directory.glob(pattern)
        if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS
    ]
    files.sort()
    return files

