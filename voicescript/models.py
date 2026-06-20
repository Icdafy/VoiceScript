from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ProgressCallback = Callable[[float, str], None]


def _clean_text(value: str) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class TranscriptSegment:
    index: int
    start_sec: float
    end_sec: float
    text: str

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("segment index must be one-based")
        if self.start_sec < 0:
            raise ValueError("segment start must be non-negative")
        if self.end_sec < self.start_sec:
            raise ValueError("segment end must be greater than or equal to start")
        object.__setattr__(self, "start_sec", round(float(self.start_sec), 3))
        object.__setattr__(self, "end_sec", round(float(self.end_sec), 3))
        object.__setattr__(self, "text", _clean_text(self.text))

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "text": self.text,
        }


@dataclass(frozen=True)
class TranscriptDocument:
    source_file: Path
    duration_sec: float
    language: str
    model: str
    segments: list[TranscriptSegment]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        source_file = Path(self.source_file)
        if self.duration_sec < 0:
            raise ValueError("duration must be non-negative")
        ordered = list(self.segments or [])
        previous_end = 0.0
        for segment in ordered:
            if segment.start_sec < previous_end - 0.001:
                raise ValueError("segments must be ordered by timestamp")
            previous_end = segment.end_sec
        object.__setattr__(self, "source_file", source_file)
        object.__setattr__(self, "duration_sec", round(float(self.duration_sec), 3))
        object.__setattr__(self, "language", _clean_text(self.language))
        object.__setattr__(self, "model", _clean_text(self.model))
        object.__setattr__(self, "segments", ordered)

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments if segment.text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": str(self.source_file),
            "duration_sec": self.duration_sec,
            "language": self.language,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "text": self.text,
            "segments": [segment.to_dict() for segment in self.segments],
        }


@dataclass(frozen=True)
class TranscriptionJobConfig:
    input_file: Path
    language: str | None
    model_profile: str
    output_dir: Path
    output_formats: tuple[str, ...] = ("txt",)
    restore_punctuation: bool = True
    enable_speaker_id: bool = False

    def __post_init__(self) -> None:
        formats = tuple(str(item).strip().lower() for item in self.output_formats if str(item).strip())
        if not formats:
            formats = ("txt",)
        object.__setattr__(self, "input_file", Path(self.input_file))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        object.__setattr__(self, "output_formats", formats)
