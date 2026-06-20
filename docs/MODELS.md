# ASR Model Notes

## Whisper large-v3

VoiceScript calls official OpenAI Whisper with model id `large-v3`, task `transcribe`, and word timestamps enabled. It does not use `turbo` because V1 explicitly targets `Whisper-large-V3`.

On GPUs with less than about 10GB VRAM, VoiceScript uses CPU fallback before loading the model.

As of v0.1.1, long files are split into 60-second WAV chunks for Whisper. Each chunk is transcribed with `large-v3`, then segment and word timestamps are shifted back onto the original absolute timeline.

## Qwen3-ASR-1.7B

VoiceScript calls `Qwen/Qwen3-ASR-1.7B` through the `qwen-asr` transformers backend. For timestamps, it loads `Qwen/Qwen3-ForcedAligner-0.6B`.

On GPUs with less than about 8GB VRAM, VoiceScript uses CPU fallback. Long audio is split into 170-second WAV chunks for timestamp-safe forced alignment, then merged back into one absolute timeline.

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
