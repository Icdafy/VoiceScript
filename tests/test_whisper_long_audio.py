import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from voicescript.backends.base import TranscriptionProgress
from voicescript.backends.whisper_backend import WhisperBackend


class FakeWhisperModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append((Path(audio_path).name, kwargs))
        index = len(self.calls)
        return {
            "language": "zh",
            "segments": [
                {
                    "start": 0.0,
                    "end": 10.0,
                    "text": f" chunk {index} ",
                    "words": [{"start": 0.0, "end": 1.0, "word": f"chunk{index}"}],
                }
            ],
        }


class WhisperLongAudioTests(unittest.TestCase):
    def test_long_audio_is_chunked_and_merged_with_absolute_timestamps(self):
        model = FakeWhisperModel()
        messages = []
        backend = WhisperBackend(chunk_seconds=60.0)
        backend._model = model

        def fake_extract(source, target, start, duration):
            target.write_bytes(b"fake wav")

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "long.m4a"
            audio_path.write_bytes(b"fake audio")
            with (
                patch(
                    "voicescript.backends.whisper_backend.probe_audio",
                    return_value=SimpleNamespace(duration=130.0),
                ),
                patch.object(backend, "_extract_chunk", side_effect=fake_extract),
            ):
                transcript = backend.transcribe(
                    audio_path,
                    TranscriptionProgress(callback=lambda message, value=None: messages.append(message)),
                )

        self.assertEqual([segment.text for segment in transcript.segments], ["chunk 1", "chunk 2", "chunk 3"])
        self.assertEqual([segment.start for segment in transcript.segments], [0.0, 60.0, 120.0])
        self.assertEqual(len(model.calls), 3)
        self.assertTrue(any("Whisper chunk 3" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
