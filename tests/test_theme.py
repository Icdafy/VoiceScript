import unittest

from voicescript.desktop.theme import ThemeMode, build_stylesheet


class ThemeTests(unittest.TestCase):
    def test_theme_stylesheets_cover_black_and_white_modes(self):
        dark = build_stylesheet(ThemeMode.BLACK)
        light = build_stylesheet(ThemeMode.WHITE)

        self.assertIn("QMainWindow", dark)
        self.assertIn("QMainWindow", light)
        self.assertNotEqual(dark, light)
        self.assertIn("44px", dark)
        self.assertIn("44px", light)


if __name__ == "__main__":
    unittest.main()
