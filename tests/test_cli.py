import argparse
import tempfile
import unittest
from pathlib import Path

from voicescript.cli import build_parser, run_transcribe_command, select_backend
from voicescript.core.transcript import Segment, Transcript


class FakeBackend:
    def transcribe(self, audio_path, progress=None):
        return Transcript(
            model="fake",
            source_file=Path(audio_path),
            duration=1.0,
            language="zh",
            segments=[Segment(start=0.0, end=1.0, text="exact transcript")],
        )


class CliTests(unittest.TestCase):
    def test_parser_accepts_two_model_choices(self):
        parser = build_parser()

        whisper_args = parser.parse_args(
            ["transcribe", "--model", "whisper-large-v3", "--input", "a.m4a", "--out", "out"]
        )
        qwen_args = parser.parse_args(
            ["transcribe", "--model", "qwen3-asr-1.7b", "--input", "a.m4a", "--out", "out"]
        )

        self.assertEqual(whisper_args.model, "whisper-large-v3")
        self.assertEqual(qwen_args.model, "qwen3-asr-1.7b")

    def test_select_backend_rejects_unknown_model(self):
        with self.assertRaises(ValueError):
            select_backend("unknown")

    def test_run_transcribe_command_uses_backend_and_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "voice.m4a"
            input_path.write_bytes(b"not real audio because backend is fake")
            args = argparse.Namespace(
                input=input_path,
                out=Path(tmp) / "exports",
                formats="txt,json",
                obsidian=False,
                obsidian_dir=None,
            )

            paths = run_transcribe_command(args, backend=FakeBackend())

        self.assertEqual(set(paths), {"txt", "json"})
        self.assertTrue(paths["txt"].name.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
