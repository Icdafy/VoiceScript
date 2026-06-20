from __future__ import annotations

from typing import Protocol

from voicescript.models import ProgressCallback, TranscriptionJobConfig, TranscriptDocument


class AsrBackend(Protocol):
    def transcribe(
        self,
        config: TranscriptionJobConfig,
        progress_callback: ProgressCallback | None = None,
    ) -> TranscriptDocument:
        """Transcribe one audio file into a timestamped transcript document."""
