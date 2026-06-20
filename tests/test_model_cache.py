import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from voicescript.backends.base import TranscriptionProgress
from voicescript.backends.qwen_backend import QWEN_ALIGNER_ID, QWEN_MODEL_ID, QwenBackend
from voicescript.backends.whisper_backend import WhisperBackend
from voicescript.core.model_cache import (
    clean_invalid_whisper_checkpoint,
    format_progress_units,
    prefetch_huggingface_repo,
)


class ModelCacheTests(unittest.TestCase):
    def test_clean_invalid_whisper_checkpoint_removes_zero_byte_file(self):
        messages = []
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "large-v3.pt"
            checkpoint.write_bytes(b"")

            removed = clean_invalid_whisper_checkpoint(
                "large-v3",
                model_dir=tmp,
                progress=TranscriptionProgress(callback=lambda message, value=None: messages.append(message)),
            )

            self.assertTrue(removed)
            self.assertFalse(checkpoint.exists())
            self.assertTrue(any("Removing incomplete Whisper checkpoint" in message for message in messages))

    def test_prefetch_huggingface_repo_emits_download_status(self):
        messages = []

        with patch("voicescript.core.model_cache.snapshot_download", return_value="C:/cache/model") as download:
            path = prefetch_huggingface_repo(
                "Qwen/Test",
                label="Qwen Test",
                progress=TranscriptionProgress(callback=lambda message, value=None: messages.append(message)),
                progress_value=0.25,
            )

        self.assertEqual(path, Path("C:/cache/model"))
        download.assert_called_once()
        self.assertIn("Checking/downloading Qwen Test", messages[0])

    def test_progress_units_use_file_counts_for_snapshot_file_progress(self):
        self.assertEqual(format_progress_units(3, 12), "3 / 12 files")
        self.assertEqual(format_progress_units(2 * 1024 * 1024, 4 * 1024 * 1024), "2.0MB / 4.0MB")

    def test_qwen_load_prefetches_main_model_and_forced_aligner_before_importing_model_class(self):
        calls = []
        backend = QwenBackend()

        class FakeTorch:
            float32 = object()
            bfloat16 = object()

            class cuda:
                @staticmethod
                def is_available():
                    return False

        class FakeQwenClass:
            @staticmethod
            def from_pretrained(*args, **kwargs):
                calls.append(("from_pretrained", args, kwargs))
                return object()

        with (
            patch("voicescript.backends.qwen_backend.prefetch_huggingface_repo") as prefetch,
            patch("voicescript.backends.qwen_backend._import_qwen_model_class", return_value=FakeQwenClass),
            patch.dict("sys.modules", {"torch": FakeTorch}),
        ):
            backend._load_model(TranscriptionProgress(callback=lambda *_: None))

        self.assertEqual([call.args[0] for call in prefetch.call_args_list], [QWEN_MODEL_ID, QWEN_ALIGNER_ID])
        self.assertEqual(calls[0][1][0], QWEN_MODEL_ID)

    def test_whisper_load_cleans_invalid_checkpoint_before_loading_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = Path(tmp) / "large-v3.pt"
            checkpoint.write_bytes(b"")
            backend = WhisperBackend(model_dir=tmp)

            class FakeTorch:
                class cuda:
                    @staticmethod
                    def is_available():
                        return False

            class FakeWhisper:
                @staticmethod
                def load_model(*args, **kwargs):
                    self.assertFalse(checkpoint.exists())
                    return object()

            with patch.dict("sys.modules", {"torch": FakeTorch, "whisper": FakeWhisper}):
                backend._load_model(TranscriptionProgress(callback=lambda *_: None))

    def test_ensure_whisper_checkpoint_downloads_with_requests_stream(self):
        from voicescript.core.model_cache import ensure_whisper_checkpoint

        payload = b"checkpoint"
        digest = hashlib.sha256(payload).hexdigest()

        class FakeWhisper:
            _MODELS = {"large-v3": f"https://example.invalid/{digest}/large-v3.pt"}

        class FakeResponse:
            headers = {"Content-Length": str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def raise_for_status(self):
                return None

            def iter_content(self, chunk_size):
                yield payload

        with tempfile.TemporaryDirectory() as tmp, patch(
            "voicescript.core.model_cache.requests.get",
            return_value=FakeResponse(),
        ) as get:
            path = ensure_whisper_checkpoint(FakeWhisper, "large-v3", model_dir=tmp)

            self.assertEqual(path.read_bytes(), payload)
            get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
