from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


def default_config_file() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "VoiceScript" / "preferences.json"
    return Path.home() / ".config" / "VoiceScript" / "preferences.json"


@dataclass(frozen=True)
class UserPreferences:
    theme: str = "light"
    output_dir: Path | None = None

    def __post_init__(self) -> None:
        theme = self.theme if self.theme in {"light", "dark"} else "light"
        output_dir = Path(self.output_dir) if self.output_dir else None
        object.__setattr__(self, "theme", theme)
        object.__setattr__(self, "output_dir", output_dir)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "theme": self.theme,
            "output_dir": str(self.output_dir) if self.output_dir else None,
        }


def load_preferences(path: Path | None = None) -> UserPreferences:
    path = Path(path or default_config_file())
    if not path.exists():
        return UserPreferences()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return UserPreferences(
        theme=str(payload.get("theme") or "light"),
        output_dir=payload.get("output_dir") or None,
    )


def save_preferences(preferences: UserPreferences, path: Path | None = None) -> None:
    path = Path(path or default_config_file())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(preferences.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
