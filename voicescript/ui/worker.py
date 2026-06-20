from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from voicescript.asr.mock import MockAsrBackend
from voicescript.asr.qwen import QwenAsrBackend
from voicescript.export.formats import write_exports
from voicescript.models import TranscriptionJobConfig, TranscriptDocument
from voicescript.runtime import ensure_std_streams


class TranscriptionWorker(QThread):
    progress = Signal(float, str)
    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, config: TranscriptionJobConfig, use_mock: bool = False) -> None:
        super().__init__()
        self.config = config
        self.use_mock = use_mock
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        ensure_std_streams()
        try:
            backend = MockAsrBackend() if self.use_mock else QwenAsrBackend(self.config.model_profile)

            def on_progress(value: float, message: str) -> None:
                if self._cancel_requested:
                    raise RuntimeError("用户已取消转录")
                self.progress.emit(value, message)

            doc: TranscriptDocument = backend.transcribe(self.config, on_progress)
            paths: list[Path] = write_exports(
                doc,
                self.config.output_dir,
                self.config.output_formats,
                self.config.restore_punctuation,
            )
            self.completed.emit(doc, paths)
        except Exception as exc:
            self.failed.emit(str(exc))
