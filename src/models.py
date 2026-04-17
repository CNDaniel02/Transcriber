from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PipelineOptions:
    model_name: str = "large-v3"
    device: str = "cuda"
    precision: str = "fp32"
    language: Optional[str] = None
    include_timestamps: bool = False
    include_speakers: bool = False
    pause_threshold_sec: float = 1.2
    max_speakers: int = 2
    ffmpeg_bin: str = "ffmpeg"
    keep_temp_files: bool = False
    output_conflict_strategy: str = "timestamp"

    def validate(self) -> None:
        if self.device not in {"cuda", "cpu"}:
            raise ValueError("device must be one of: cuda, cpu")
        if self.precision not in {"fp32", "fp16"}:
            raise ValueError("precision must be one of: fp32, fp16")
        if self.pause_threshold_sec < 0:
            raise ValueError("pause_threshold_sec must be >= 0")
        if self.max_speakers < 1:
            raise ValueError("max_speakers must be >= 1")
        if self.output_conflict_strategy not in {"timestamp", "sequence", "overwrite"}:
            raise ValueError("output_conflict_strategy must be one of: timestamp, sequence, overwrite")


@dataclass(frozen=True)
class FileTranscriptionResult:
    input_file: Path
    output_file: Path
    device_used: str
    language: str
    segment_count: int
    elapsed_seconds: float


@dataclass
class BatchTranscriptionResult:
    total_files: int = 0
    success_files: int = 0
    failed_files: int = 0
    outputs: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
