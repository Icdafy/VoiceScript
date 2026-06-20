# VoiceScript v0.1.4 Release Notes

Bugfix release addressing runtime crashes in windowed mode, theme persistence, upload behavior, and a new custom output directory feature.

## Fixed

- **Whisper large-v3 crash** (`'NoneType' object has no attribute 'write'`): PyInstaller windowed builds set `sys.stdout`/`sys.stderr` to `None`; tqdm progress bars in Whisper and huggingface_hub attempted to write to these `None` streams. A new `ensure_std_streams()` guard replaces missing streams with safe no-op writers at app startup and in the worker thread.
- **Qwen3-ASR stuck at "Checking/downloading"**: Same root cause as above; the huggingface_hub snapshot downloader's tqdm crashed silently in the background thread.
- **Theme not saved across restarts**: Theme selection (black/white) was only stored in memory. Now persisted to `~/.cache/voicescript/preferences.json` and restored on launch.
- **Auto-start transcription on upload**: Previously, selecting or dropping an audio file immediately started transcription. Now the default is to wait for the user to click "Start Transcription".

## New Features

- **Custom save location**: A new "Set Save Location" button in the sidebar lets users choose a persistent output directory for exported transcripts. The setting is saved to preferences and reused across sessions.

## Changed Files

| File | Change |
|------|--------|
| `voicescript/__init__.py` | Version bump to 0.1.4 |
| `pyproject.toml` | Version bump to 0.1.4 |
| `voicescript/core/runtime.py` | New module: null-stream guard |
| `voicescript/core/settings.py` | Added `UserPreferences`, `load_preferences`, `save_preferences` |
| `voicescript/desktop/app.py` | Theme persistence, auto-start disabled, custom output dir UI |
| `voicescript/desktop/worker.py` | Stream guard in worker thread |

## Notes

- The preferences file is stored at `~/.cache/voicescript/preferences.json`.
- Existing users upgrading from v0.1.3 will start with default preferences (black theme, no custom directory) on first launch of v0.1.4.
