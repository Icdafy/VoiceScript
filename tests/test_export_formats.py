import json
from pathlib import Path

from voicescript.export.formats import (
    export_json,
    export_markdown,
    export_srt,
    export_txt,
)
from voicescript.models import TranscriptDocument, TranscriptSegment


def _doc() -> TranscriptDocument:
    return TranscriptDocument(
        source_file=Path("meeting.m4a"),
        duration_sec=65.5,
        language="Chinese",
        model="Qwen/Qwen3-ASR-0.6B",
        segments=[
            TranscriptSegment(index=1, start_sec=0.0, end_sec=2.4, text="第一句话。"),
            TranscriptSegment(index=2, start_sec=62.0, end_sec=65.5, text="第二句话。"),
        ],
    )


def test_txt_export_contains_timestamps_and_no_summary():
    text = export_txt(_doc())

    assert "[00:00:00.000 - 00:00:02.400] 第一句话。" in text
    assert "[00:01:02.000 - 00:01:05.500] 第二句话。" in text
    assert "总结" not in text
    assert "纪要" not in text


def test_markdown_srt_and_json_exports_are_complete():
    doc = _doc()

    markdown = export_markdown(doc)
    srt = export_srt(doc)
    payload = json.loads(export_json(doc))

    assert "# meeting" in markdown
    assert "| 1 | 00:00:00.000 | 00:00:02.400 | 第一句话。 |" in markdown
    assert "00:00:00,000 --> 00:00:02,400" in srt
    assert payload["segments"][1]["text"] == "第二句话。"


def test_punctuation_can_be_removed_without_rewriting_words():
    text = export_txt(_doc(), restore_punctuation=False)

    assert "第一句话" in text
    assert "第一句话。" not in text
