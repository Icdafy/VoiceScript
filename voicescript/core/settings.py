from __future__ import annotations

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
