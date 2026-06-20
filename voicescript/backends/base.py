from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from voicescript.core.transcript import Transcript


ProgressCallback = Callable[[str, float | None], None]


@dataclass(frozen=True)
class BackendInfo:
    key: str
    label: str
    model_id: str
    needs_timestamps_model: bool
    notes: str = ""


@dataclass
class TranscriptionProgress:
    callback: ProgressCallback | None = None
    cancelled: Callable[[], bool] | None = None

    def emit(self, message: str, value: float | None = None) -> None:
        if self.callback:
            self.callback(message, value)

    def is_cancelled(self) -> bool:
        return bool(self.cancelled and self.cancelled())

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise RuntimeError("transcription cancelled")


class ASRBackend(ABC):
    info: BackendInfo

    @abstractmethod
    def transcribe(self, audio_path: Path, progress: TranscriptionProgress | None = None) -> Transcript:
        raise NotImplementedError
