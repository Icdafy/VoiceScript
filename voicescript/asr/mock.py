from __future__ import annotations

from pathlib import Path

from voicescript.models import ProgressCallback, TranscriptionJobConfig, TranscriptDocument, TranscriptSegment


class MockAsrBackend:
    def transcribe(
        self,
        config: TranscriptionJobConfig,
        progress_callback: ProgressCallback | None = None,
    ) -> TranscriptDocument:
        if progress_callback:
            progress_callback(0.1, "模拟加载模型")
            progress_callback(0.6, "模拟转录")
            progress_callback(1.0, "模拟完成")
        source = Path(config.input_file)
        return TranscriptDocument(
            source_file=source,
            duration_sec=1.0,
            language=config.language or "Chinese",
            model=f"mock-{config.model_profile}",
            segments=[
                TranscriptSegment(index=1, start_sec=0.0, end_sec=1.0, text="模拟转录文本。"),
            ],
        )
