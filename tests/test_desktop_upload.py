import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from voicescript.desktop.app import MainWindow


class UploadStartsTranscriptionWindow(MainWindow):
    def __init__(self):
        self.started = 0
        super().__init__(auto_start_on_file_select=True)

    def _refresh_environment(self):
        pass

    def _start_transcription(self):
        self.started += 1


class DesktopUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_uploading_supported_audio_starts_transcription(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.m4a"
            path.write_bytes(b"fake")
            window = UploadStartsTranscriptionWindow()
            try:
                window._set_audio_file(path)

                self.assertEqual(window.audio_path, path)
                self.assertEqual(window.started, 1)
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
