from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    cache_dir: Path
    default_export_dir: Path
    obsidian_dir: Path


def default_settings() -> AppSettings:
    root = Path.cwd()
    return AppSettings(
        cache_dir=Path.home() / ".cache" / "voicescript",
        default_export_dir=root / "transcripts",
        obsidian_dir=Path("F:/声笺录/声笺录/VoiceScript"),
    )


PREFERENCES_FILENAME = "preferences.json"


@dataclass
class UserPreferences:
    """User-adjustable preferences persisted between runs."""

    theme: str = "black"
    output_dir: str | None = None


def preferences_path(cache_dir: Path | str) -> Path:
    return Path(cache_dir) / PREFERENCES_FILENAME


def load_preferences(cache_dir: Path | str) -> UserPreferences:
    path = preferences_path(cache_dir)
    if not path.exists():
        return UserPreferences()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return UserPreferences()
    if not isinstance(data, dict):
        return UserPreferences()
    theme = str(data.get("theme") or "black").lower()
    if theme not in ("black", "white"):
        theme = "black"
    output_dir = data.get("output_dir")
    return UserPreferences(
        theme=theme,
        output_dir=str(output_dir) if output_dir else None,
    )


def save_preferences(cache_dir: Path | str, preferences: UserPreferences) -> Path:
    path = preferences_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "theme": preferences.theme,
        "output_dir": preferences.output_dir,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
