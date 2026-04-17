from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import torch
import whisper


@dataclass(frozen=True)
class TranscribeConfig:
    model_name: str = "large-v3"
    requested_device: str = "cuda"
    precision: str = "fp32"
    language: Optional[str] = None


@dataclass(frozen=True)
class TranscribeResult:
    text: str
    segments: list[dict[str, Any]]
    language: Optional[str]
    model_name: str
    device_used: str


class WhisperTranscriber:
    def __init__(
        self,
        config: TranscribeConfig,
        cache_dir: Path,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config
        self.cache_dir = cache_dir
        self.logger = logger or logging.getLogger(__name__)
        self.model = None
        self.device_used = "cpu"

    def _resolve_device(self) -> str:
        if self.config.requested_device == "cuda":
            if torch.cuda.is_available():
                return "cuda"
            self.logger.warning("CUDA requested but unavailable. Falling back to CPU.")
        return "cpu"

    def _use_fp16(self) -> bool:
        return self.config.precision.lower() == "fp16" and self.device_used == "cuda"

    def load_model(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.device_used = self._resolve_device()

        try:
            self.model = whisper.load_model(
                self.config.model_name,
                device=self.device_used,
                download_root=str(self.cache_dir),
            )
            return
        except Exception as exc:
            if self.device_used == "cuda":
                self.logger.warning("Failed to load model on CUDA: %s", exc)
                self.logger.warning("Retrying model load on CPU.")
                self.device_used = "cpu"
                self.model = whisper.load_model(
                    self.config.model_name,
                    device=self.device_used,
                    download_root=str(self.cache_dir),
                )
                return
            raise

    def transcribe(self, audio_path: Path) -> TranscribeResult:
        if self.model is None:
            self.load_model()

        options: dict[str, Any] = {
            "task": "transcribe",
            "fp16": self._use_fp16(),
            "verbose": False,
        }
        if self.config.language:
            options["language"] = self.config.language

        result = self.model.transcribe(str(audio_path), **options)
        segments: list[dict[str, Any]] = []
        for item in result.get("segments", []):
            segments.append(
                {
                    "id": int(item.get("id", len(segments))),
                    "start": float(item.get("start", 0.0)),
                    "end": float(item.get("end", 0.0)),
                    "text": str(item.get("text", "")).strip(),
                }
            )

        return TranscribeResult(
            text=str(result.get("text", "")).strip(),
            segments=segments,
            language=result.get("language"),
            model_name=self.config.model_name,
            device_used=self.device_used,
        )
