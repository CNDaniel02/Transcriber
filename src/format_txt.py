from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def format_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def render_transcript_txt(
    metadata: dict[str, str],
    segments: list[dict[str, Any]],
    include_timestamps: bool = True,
    include_speakers: bool = True,
) -> str:
    lines: list[str] = []
    lines.append("=== TRANSCRIPT ===")
    lines.append(f"Generated At: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Source File: {metadata.get('source_file', '')}")
    lines.append(f"Source Type: {metadata.get('source_type', '')}")
    lines.append(f"Model: {metadata.get('model', '')}")
    lines.append(f"Device: {metadata.get('device', '')}")
    lines.append(f"Precision: {metadata.get('precision', '')}")
    lines.append(f"Language: {metadata.get('language', '')}")
    lines.append(f"Segments: {metadata.get('segments', '')}")
    lines.append("")
    lines.append("=== SEGMENTS ===")

    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue

        parts: list[str] = []
        if include_timestamps:
            start = format_timestamp(float(segment.get("start", 0.0)))
            end = format_timestamp(float(segment.get("end", 0.0)))
            parts.append(f"[{start} -> {end}]")
        if include_speakers:
            speaker = str(segment.get("speaker", "Speaker_1"))
            parts.append(f"{speaker}:")
        parts.append(text)
        lines.append(" ".join(parts))

    lines.append("")
    return "\n".join(lines)


def write_transcript_txt(
    output_path: Path,
    metadata: dict[str, str],
    segments: list[dict[str, Any]],
    include_timestamps: bool = True,
    include_speakers: bool = True,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_transcript_txt(
        metadata=metadata,
        segments=segments,
        include_timestamps=include_timestamps,
        include_speakers=include_speakers,
    )
    output_path.write_text(content, encoding="utf-8")

