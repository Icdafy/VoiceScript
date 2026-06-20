import json
import tempfile
import unittest
from pathlib import Path

from voicescript.core.exporters import export_transcript, format_srt_timestamp
from voicescript.core.transcript import Segment, Transcript


def sample_transcript() -> Transcript:
    return Transcript(
        model="whisper-large-v3",
        source_file=Path("meeting.m4a"),
        duration=4.2,
        language="zh",
        segments=[
            Segment(start=0.0, end=1.5, text="first exact line"),
            Segment(start=1.5, end=4.2, text="second exact line"),
        ],
    )


class ExporterTests(unittest.TestCase):
    def test_srt_timestamp_uses_comma_milliseconds(self):
        self.assertEqual(format_srt_timestamp(3723.456), "01:02:03,456")

    def test_exporters_preserve_segment_text_without_summary(self):
        transcript = sample_transcript()
        with tempfile.TemporaryDirectory() as tmp:
            paths = export_transcript(transcript, Path(tmp), formats=("md", "txt", "srt", "json"))

            txt = paths["txt"].read_text(encoding="utf-8")
            md = paths["md"].read_text(encoding="utf-8")
            srt = paths["srt"].read_text(encoding="utf-8")
            data = json.loads(paths["json"].read_text(encoding="utf-8"))

        self.assertEqual(txt, "first exact line\nsecond exact line\n")
        self.assertIn("[00:00.000 -> 00:01.500] first exact line", md)
        self.assertIn("00:00:00,000 --> 00:00:01,500", srt)
        self.assertEqual(data["segments"][1]["text"], "second exact line")
        self.assertNotIn("summary", md.lower())
        self.assertNotIn("minutes", md.lower())


if __name__ == "__main__":
    unittest.main()
