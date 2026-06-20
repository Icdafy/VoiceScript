# VoiceScript v0.1.3 Release Notes

Bugfix release for first-run ASR model setup still appearing stuck or failed.

## Fixed

- Qwen now explicitly checks/downloads both `Qwen/Qwen3-ASR-1.7B` and `Qwen/Qwen3-ForcedAligner-0.6B` before loading the model into memory.
- Whisper now removes zero-byte `large-v3.pt` checkpoints and downloads `large-v3` through a streaming `requests` downloader instead of the failing `urllib` path.
- Model download progress is emitted to the UI instead of leaving the progress bar at 5%.
- The desktop progress bar no longer moves backward when switching from model setup to transcription.

## Verified

- Qwen loaded successfully on the current Windows machine after cache repair.
- Qwen transcribed an 8-second sample from the user's M4A file.
- Whisper downloaded and verified `large-v3`, then transcribed a 30-second sample from the user's M4A file.

## Notes

- First-run downloads are large: Whisper large-v3 is about 2.94GB; Qwen3-ASR plus forced aligner are about 6GB in cache.
- With CPU-only Torch, transcription works but is slow. The UI now shows progress rather than looking frozen.
