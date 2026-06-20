from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentItem:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, str | bool]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


def collect_environment() -> dict[str, EnvironmentItem]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return {
        "python": EnvironmentItem(
            name="Python",
            ok=sys.version_info >= (3, 12),
            detail=sys.version.split()[0],
        ),
        "ffmpeg": EnvironmentItem(
            name="ffmpeg",
            ok=bool(ffmpeg),
            detail=ffmpeg or "missing",
        ),
        "ffprobe": EnvironmentItem(
            name="ffprobe",
            ok=bool(ffprobe),
            detail=ffprobe or "missing",
        ),
    }
