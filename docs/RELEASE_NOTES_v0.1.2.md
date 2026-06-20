# VoiceScript v0.1.2 Release Notes

Bugfix release for both ASR model options failing from the packaged Windows app.

## Fixed

- The Windows package now includes OpenAI Whisper runtime assets such as `mel_filters.npz` and tokenizer files.
- The Windows package now includes Qwen3-ASR forced-alignment runtime data such as `korean_dict_jieba.dict`.
- PyInstaller now collects Whisper, Qwen3-ASR, and `tiktoken_ext` dynamic modules explicitly.
- Qwen package module discovery no longer imports `qwen_asr` during packaging, avoiding the nagisa/DyNet failure seen on Windows paths with Chinese characters.

## Notes

- The app folder is `F:\声笺录\VoiceScript\dist\VoiceScript` after a local build.
- The source repository folder is `F:\声笺录\VoiceScript`.
- The Obsidian knowledge folder is `F:\声笺录\声笺录\VoiceScript`.
- Model weights are still downloaded on first use and are not bundled in GitHub releases.
