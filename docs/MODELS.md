# ASR Model Notes

## Whisper large-v3

VoiceScript calls official OpenAI Whisper with model id `large-v3`, task `transcribe`, and word timestamps enabled. It does not use `turbo` because V1 explicitly targets `Whisper-large-V3`.

On GPUs with less than about 10GB VRAM, VoiceScript uses CPU fallback before loading the model.

As of v0.1.1, long files are split into 60-second WAV chunks for Whisper. Each chunk is transcribed with `large-v3`, then segment and word timestamps are shifted back onto the original absolute timeline.

As of v0.1.2, the Windows package includes Whisper's runtime assets, including mel filters and tokenizer files. Model weights are still downloaded to the user's cache on first use.

As of v0.1.3, VoiceScript removes broken zero-byte Whisper checkpoints and downloads `large-v3` with a streaming HTTP downloader that reports progress in the UI.

## Qwen3-ASR-1.7B

VoiceScript calls `Qwen/Qwen3-ASR-1.7B` through the `qwen-asr` transformers backend. For timestamps, it loads `Qwen/Qwen3-ForcedAligner-0.6B`.

On GPUs with less than about 8GB VRAM, VoiceScript uses CPU fallback. Long audio is split into 170-second WAV chunks for timestamp-safe forced alignment, then merged back into one absolute timeline.

As of v0.1.2, the Windows package includes Qwen's forced-alignment runtime dictionary and collects Qwen modules without importing the top-level package during packaging. This avoids the nagisa/DyNet Windows path issue during build collection.

As of v0.1.3, VoiceScript explicitly checks/downloads both `Qwen/Qwen3-ASR-1.7B` and `Qwen/Qwen3-ForcedAligner-0.6B` before model initialization, so first-run setup shows progress instead of appearing stuck at model loading.

## Output Rule

Both backends normalize into the same schema:

```json
{
  "model": "whisper-large-v3",
  "source_file": "audio.m4a",
  "duration": 123.4,
  "language": "zh",
  "segments": [
    { "start": 0.0, "end": 4.2, "text": "recognized speech" }
  ]
}
```

Exporters only format this text. They do not summarize or rewrite it.
