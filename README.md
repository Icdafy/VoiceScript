# VoiceScript 声笺录

声落成笺，语转为文。

VoiceScript is a local-first Windows desktop tool for turning uploaded audio files into complete, timestamped text transcripts. V1 does not summarize, rewrite, organize meeting minutes, or perform semantic extraction. It preserves the recognized transcript text in time order.

## V1 Features

- Upload full audio files from Apple and Android workflows: `.m4a`, `.aac`, `.caf`, `.amr`, `.3gp`, `.ogg`, `.opus`, `.mp3`, `.wav`, `.flac`.
- Uploaded audio starts transcription automatically with the currently selected model.
- Long audio is processed in chunks so the UI keeps reporting progress instead of looking frozen.
- Choose between two strongest configured ASR options:
  - `Whisper large-v3` from OpenAI Whisper.
  - `Qwen3-ASR-1.7B` with `Qwen3-ForcedAligner-0.6B` timestamps.
- Export complete time-segmented transcripts as `.md`, `.txt`, `.srt`, and `.json`.
- Save transcript artifacts into the Obsidian knowledge folder `F:\声笺录\声笺录\VoiceScript`.
- Toggle black and white UI themes.
- Check local runtime status for Python, ffmpeg, ffprobe, Torch/CUDA, disk space, and model-cache readiness.

## Hardware Note

The target machine currently has an RTX 3060 Laptop GPU with about 4GB VRAM. VoiceScript keeps the selected model identity, but it may fall back to CPU or low-batch behavior when GPU memory is too small for `Whisper large-v3` or Qwen timestamp alignment. CPU fallback is slower, especially for long audio.

For multi-hour audio, v0.1.1 and later show chunk-level progress while transcription is running. First model download can still take time because model weights are not bundled in the release.

v0.1.2 fixes the Windows package so Whisper and Qwen runtime assets are included in the app folder. Model weights are still downloaded into the user cache instead of being committed or bundled.

## Quick Start

```powershell
cd F:\声笺录\VoiceScript
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m voicescript env
.\.venv\Scripts\python -m voicescript.desktop
```

Command-line transcription:

```powershell
.\.venv\Scripts\python -m voicescript transcribe `
  --model whisper-large-v3 `
  --input "F:\path\audio.m4a" `
  --out "F:\声笺录\VoiceScript\transcripts" `
  --formats md,txt,srt,json `
  --obsidian
```

## Windows Build

```powershell
.\scripts\build-windows.ps1
```

The local development release folder is generated under `F:\声笺录\VoiceScript\dist\VoiceScript`.

## What V1 Intentionally Does Not Do

- No meeting minutes.
- No summaries.
- No semantic restructuring.
- No speaker diarization.
- No real-time microphone transcription.
- No bundled model weights in GitHub or the Windows release.

These may be future roadmap items, but they are outside the current release.

## Model Sources

- OpenAI Whisper: <https://github.com/openai/whisper>, `large-v3`, MIT license.
- Qwen3-ASR: <https://github.com/QwenLM/Qwen3-ASR>, `Qwen/Qwen3-ASR-1.7B`, Apache-2.0 license.
- Qwen3-ASR blog: <https://qwen.ai/blog?id=qwen3asr>.

See [NOTICE.md](NOTICE.md) for third-party notices.
