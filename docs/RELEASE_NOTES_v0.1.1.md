# VoiceScript v0.1.1 Release Notes

Bugfix release for uploaded audio appearing unresponsive.

## Fixed

- Uploading or dragging in a supported audio file now starts transcription automatically with the selected model.
- Whisper large-v3 now processes long audio in 60-second chunks and merges segment timestamps back to the original timeline.
- The UI receives chunk-level progress messages during long Whisper transcription instead of waiting for the whole file to finish.
- Local uploaded audio files are ignored by Git so large user samples are not accidentally committed.

## Notes

- The local test sample `合肥中科华控-董秘.m4a` is an iPhone Voice Memos AAC/M4A file, about 212MB and 7394 seconds long.
- First model download can still take time because model weights are intentionally not bundled in the release.
