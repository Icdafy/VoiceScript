# Third-Party Notices

VoiceScript integrates with open-source ASR projects but does not vendor or commit their model weights.

## OpenAI Whisper

- Repository: https://github.com/openai/whisper
- Configured model: `large-v3`
- Local source reference during development: `F:\声笺录\whisper-20250625`
- License: MIT

## Qwen3-ASR

- Repository: https://github.com/QwenLM/Qwen3-ASR
- Configured ASR model: `Qwen/Qwen3-ASR-1.7B`
- Configured timestamp model: `Qwen/Qwen3-ForcedAligner-0.6B`
- Python package: `qwen-asr==0.0.6`
- License: Apache-2.0

Model weights are downloaded into user cache directories at runtime/setup time and are intentionally excluded from this repository and release artifacts.
