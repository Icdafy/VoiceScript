import unittest
from pathlib import Path
from unittest.mock import patch

from voicescript.core.environment import check_environment


class EnvironmentTests(unittest.TestCase):
    @patch("voicescript.core.environment.shutil.which")
    @patch("voicescript.core.environment.shutil.disk_usage")
    def test_environment_check_reports_tools_and_disk(self, disk_usage, which):
        disk_usage.return_value = (100, 50, 25)
        which.side_effect = lambda name: f"C:/tools/{name}.exe" if name in {"ffmpeg", "ffprobe"} else None

        report = check_environment(cache_dir=Path("C:/cache"))

        self.assertTrue(report.ffmpeg.available)
        self.assertTrue(report.ffprobe.available)
        self.assertEqual(report.disk_free_bytes, 25)
        self.assertIsInstance(report.torch.available, bool)


if __name__ == "__main__":
    unittest.main()
