import sys
import unittest

from voicescript.backends.qwen_backend import install_nagisa_import_fallback


class QwenCompatTests(unittest.TestCase):
    def test_nagisa_fallback_exposes_tagging_words(self):
        original = sys.modules.pop("nagisa", None)
        try:
            install_nagisa_import_fallback(force=True)
            import nagisa

            self.assertEqual(nagisa.tagging("abc").words, ["abc"])
        finally:
            sys.modules.pop("nagisa", None)
            if original is not None:
                sys.modules["nagisa"] = original


if __name__ == "__main__":
    unittest.main()
