import unittest

from voicescript.build_support import (
    collect_asr_datas,
    collect_asr_hiddenimports,
    collect_package_modules_without_import,
)


class PyInstallerAssetsTests(unittest.TestCase):
    def test_asr_runtime_data_files_are_collected(self):
        datas = collect_asr_datas()
        normalized = {(source.replace("\\", "/"), target.replace("\\", "/")) for source, target in datas}

        self.assertTrue(any(source.endswith("/whisper/assets/mel_filters.npz") for source, _ in normalized))
        self.assertTrue(any(source.endswith("/whisper/assets/multilingual.tiktoken") for source, _ in normalized))
        self.assertTrue(any(source.endswith("/qwen_asr/inference/assets/korean_dict_jieba.dict") for source, _ in normalized))

    def test_dynamic_asr_modules_are_collected(self):
        hiddenimports = collect_asr_hiddenimports()

        self.assertIn("whisper", hiddenimports)
        self.assertIn("whisper.transcribe", hiddenimports)
        self.assertIn("tiktoken_ext.openai_public", hiddenimports)
        self.assertIn("qwen_asr.inference.qwen3_asr", hiddenimports)
        self.assertIn("qwen_asr.inference.qwen3_forced_aligner", hiddenimports)
        self.assertIn("qwen_asr.core.transformers_backend.processing_qwen3_asr", hiddenimports)

    def test_qwen_modules_are_listed_without_importing_qwen_asr(self):
        modules = collect_package_modules_without_import("qwen_asr")

        self.assertIn("qwen_asr", modules)
        self.assertIn("qwen_asr.inference.qwen3_asr", modules)
        self.assertIn("qwen_asr.core.transformers_backend.modeling_qwen3_asr", modules)


if __name__ == "__main__":
    unittest.main()
