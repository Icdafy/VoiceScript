import unittest
from pathlib import Path

from voicescript.backends.base import BackendInfo, TranscriptionProgress
from voicescript.backends.qwen_backend import merge_qwen_chunk_results, normalize_qwen_result
from voicescript.backends.whisper_backend import normalize_whisper_result


class BackendContractTests(unittest.TestCase):
    def test_backend_info_exposes_model_identity_and_requirements(self):
        info = BackendInfo(
            key="whisper-large-v3",
            label="Whisper large-v3",
            model_id="large-v3",
            needs_timestamps_model=False,
        )
        self.assertEqual(info.key, "whisper-large-v3")
        self.assertFalse(info.needs_timestamps_model)

    def test_progress_is_cancel_checked(self):
        progress = TranscriptionProgress(cancelled=lambda: True)
        self.assertTrue(progress.is_cancelled())

    def test_whisper_result_normalizes_segments(self):
        result = normalize_whisper_result(
            source=Path("voice.wav"),
            duration=2.0,
            raw={
                "language": "zh",
                "segments": [
                    {"start": 0, "end": 1, "text": " one "},
                    {"start": 1, "end": 2, "text": " two "},
                ],
            },
        )
        self.assertEqual(result.model, "whisper-large-v3")
        self.assertEqual(result.text, "one\ntwo")

    def test_qwen_result_normalizes_forced_alignment_items(self):
        class Item:
            def __init__(self, text, start_time, end_time):
                self.text = text
                self.start_time = start_time
                self.end_time = end_time

        class Raw:
            language = "Chinese"
            text = "你好世界"
            time_stamps = [Item("你好", 0.0, 0.5), Item("世界", 0.5, 1.2)]

        result = normalize_qwen_result(Path("voice.m4a"), 1.2, Raw())

        self.assertEqual(result.model, "qwen3-asr-1.7b")
        self.assertEqual(result.segments[0].text, "你好世界")
        self.assertEqual(result.segments[0].words[1].text, "世界")

    def test_qwen_chunk_merge_keeps_absolute_time_order(self):
        first = normalize_qwen_result(
            Path("voice.m4a"),
            1.0,
            type("Raw", (), {"language": "Chinese", "text": "A", "time_stamps": None})(),
            offset=0.0,
        )
        second = normalize_qwen_result(
            Path("voice.m4a"),
            1.0,
            type("Raw", (), {"language": "Chinese", "text": "B", "time_stamps": None})(),
            offset=1.0,
        )

        merged = merge_qwen_chunk_results(Path("voice.m4a"), 2.0, [first, second])

        self.assertEqual(merged.text, "A\nB")
        self.assertEqual(merged.segments[1].start, 1.0)


if __name__ == "__main__":
    unittest.main()
