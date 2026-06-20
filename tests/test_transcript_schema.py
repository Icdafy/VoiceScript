from pathlib import Path

import pytest

from voicescript.models import TranscriptDocument, TranscriptSegment


def test_transcript_document_rejects_out_of_order_segments():
    with pytest.raises(ValueError, match="ordered"):
        TranscriptDocument(
            source_file=Path("meeting.m4a"),
            duration_sec=8.0,
            language="Chinese",
            model="Qwen/Qwen3-ASR-0.6B",
            segments=[
                TranscriptSegment(index=1, start_sec=4.0, end_sec=5.0, text="第二段"),
                TranscriptSegment(index=2, start_sec=3.0, end_sec=4.0, text="第一段"),
            ],
        )


def test_transcript_document_exposes_only_raw_transcript_fields():
    doc = TranscriptDocument(
        source_file=Path("会议记录.m4a"),
        duration_sec=2.0,
        language="Chinese",
        model="Qwen/Qwen3-ASR-0.6B",
        segments=[
            TranscriptSegment(index=1, start_sec=0.0, end_sec=2.0, text="今天开始讨论项目进展。"),
        ],
    )

    payload = doc.to_dict()

    assert payload["text"] == "今天开始讨论项目进展。"
    assert "summary" not in payload
    assert "minutes" not in payload
    assert "abstract" not in payload
    assert payload["segments"][0] == {
        "index": 1,
        "start_sec": 0.0,
        "end_sec": 2.0,
        "text": "今天开始讨论项目进展。",
    }
