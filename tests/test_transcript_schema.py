import unittest
from pathlib import Path

from voicescript.core.transcript import Segment, Transcript, Word


class TranscriptSchemaTests(unittest.TestCase):
    def test_transcript_accepts_ordered_segments_and_words(self):
        transcript = Transcript(
            model="whisper-large-v3",
            source_file=Path("sample.m4a"),
            duration=3.0,
            language="zh",
            segments=[
                Segment(
                    start=0.0,
                    end=1.25,
                    text="hello",
                    words=[Word(start=0.0, end=0.4, text="hello")],
                ),
                Segment(start=1.25, end=3.0, text="world"),
            ],
        )

        self.assertEqual(transcript.text, "hello\nworld")
        self.assertEqual(transcript.segments[0].words[0].text, "hello")

    def test_segment_rejects_invalid_time_range(self):
        with self.assertRaises(ValueError):
            Segment(start=4.0, end=3.0, text="bad")

    def test_transcript_rejects_out_of_order_segments(self):
        with self.assertRaises(ValueError):
            Transcript(
                model="qwen3-asr-1.7b",
                source_file=Path("sample.opus"),
                duration=10.0,
                language="Chinese",
                segments=[
                    Segment(start=3.0, end=4.0, text="late"),
                    Segment(start=2.0, end=3.0, text="early"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
