from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _clean_text(value: str) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("word start must be non-negative")
        if self.end < self.start:
            raise ValueError("word end must be greater than or equal to start")
        object.__setattr__(self, "text", _clean_text(self.text))

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "text": self.text}


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("segment start must be non-negative")
        if self.end < self.start:
            raise ValueError("segment end must be greater than or equal to start")
        object.__setattr__(self, "text", _clean_text(self.text))
        object.__setattr__(self, "words", list(self.words or []))
        for word in self.words:
            if word.start < self.start or word.end > self.end:
                raise ValueError("word timestamps must be inside segment range")

    def shifted(self, offset: float) -> "Segment":
        return Segment(
            start=self.start + offset,
            end=self.end + offset,
            text=self.text,
            words=[Word(w.start + offset, w.end + offset, w.text) for w in self.words],
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }
        if self.words:
            payload["words"] = [word.to_dict() for word in self.words]
        return payload


@dataclass(frozen=True)
class Transcript:
    model: str
    source_file: Path
    duration: float
    language: str
    segments: list[Segment]

    def __post_init__(self) -> None:
        if not str(self.model).strip():
            raise ValueError("model is required")
        source = Path(self.source_file)
        if not str(source):
            raise ValueError("source_file is required")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")

        ordered = list(self.segments or [])
        previous_end = 0.0
        for index, segment in enumerate(ordered):
            if index > 0 and segment.start < previous_end - 0.001:
                raise ValueError("segments must be ordered by timestamp")
            previous_end = segment.end

        object.__setattr__(self, "source_file", source)
        object.__setattr__(self, "language", str(self.language or ""))
        object.__setattr__(self, "segments", ordered)

    @property
    def text(self) -> str:
        return "\n".join(segment.text for segment in self.segments if segment.text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "source_file": str(self.source_file),
            "duration": self.duration,
            "language": self.language,
            "segments": [segment.to_dict() for segment in self.segments],
        }
