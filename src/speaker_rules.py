from __future__ import annotations

from typing import Any, Iterable


def assign_speakers(
    segments: Iterable[dict[str, Any]],
    pause_threshold_sec: float = 1.2,
    max_speakers: int = 2,
) -> list[dict[str, Any]]:
    labeled: list[dict[str, Any]] = []
    previous_end = None
    speaker_id = 1
    max_speakers = max(1, max_speakers)

    # Rule-only baseline: switch speaker when silence gap is larger than threshold.
    for segment in segments:
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", 0.0))
        if previous_end is not None and (start - previous_end) >= pause_threshold_sec:
            speaker_id = (speaker_id % max_speakers) + 1

        enriched = dict(segment)
        enriched["start"] = start
        enriched["end"] = end
        enriched["speaker"] = f"Speaker_{speaker_id}"
        labeled.append(enriched)
        previous_end = end

    return labeled
