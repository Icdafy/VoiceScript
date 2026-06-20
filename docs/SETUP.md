# VoiceScript Setup

## Requirements

- Windows 10/11.
- Python 3.11 or newer.
- Git.
- ffmpeg and ffprobe on `PATH`.
- Sufficient disk space for model caches.

## Install Runtime

```powershell
cd F:\声笺录\VoiceScript
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m voicescript env
```

First transcription may download large model weights. Keep those caches outside Git.

## Run Desktop

```powershell
.\.venv\Scripts\python -m voicescript.desktop
```

## Run CLI

```powershell
.\.venv\Scripts\python -m voicescript transcribe --model whisper-large-v3 --input audio.m4a --out transcripts --formats md,txt,srt,json
```
