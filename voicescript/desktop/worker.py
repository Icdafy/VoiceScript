from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from voicescript.backends.base import TranscriptionProgress
from voicescript.cli import select_backend


class TranscriptionWorker(QThread):
    progress = Signal(str, object)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, model_key: str, audio_path: Path) -> None:
        super().__init__()
        self.model_key = model_key
        self.audio_path = Path(audio_path)
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            backend = select_backend(self.model_key)
            progress = TranscriptionProgress(
                callback=lambda message, value=None: self.progress.emit(message, value),
                cancelled=lambda: self._cancelled,
            )
            transcript = backend.transcribe(self.audio_path, progress=progress)
            if self._cancelled:
                self.failed.emit("Transcription cancelled.")
                return
            self.completed.emit(transcript)
        except Exception as exc:
            self.failed.emit(str(exc))
