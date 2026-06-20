import unittest
from pathlib import Path

from voicescript.core.audio import SUPPORTED_AUDIO_EXTENSIONS, is_supported_audio_file, probe_audio


class AudioProbeTests(unittest.TestCase):
    def test_supports_common_apple_and_android_audio_extensions(self):
        expected = {
            ".m4a",
            ".aac",
            ".caf",
            ".amr",
            ".3gp",
            ".ogg",
            ".opus",
            ".mp3",
            ".wav",
            ".flac",
        }
        self.assertTrue(expected.issubset(SUPPORTED_AUDIO_EXTENSIONS))
        for suffix in expected:
            self.assertTrue(is_supported_audio_file(Path(f"voice{suffix}")))

    def test_rejects_unknown_audio_extension(self):
        self.assertFalse(is_supported_audio_file(Path("voice.txt")))

    def test_probe_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            probe_audio(Path("missing.m4a"))


if __name__ == "__main__":
    unittest.main()
