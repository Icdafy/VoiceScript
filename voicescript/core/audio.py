from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_AUDIO_EXTENSIONS = {
    ".3gp",
    ".aac",
    ".amr",
    ".caf",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
}


@dataclass(frozen=True)
class AudioProbe:
    path: Path
    duration: float
    format_name: str
    sample_rate: int | None
    channels: int | None
    size_bytes: int


def is_supported_audio_file(path: Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def require_ffmpeg_tool(tool_name: str = "ffprobe") -> str:
    exe = shutil.which(tool_name)
    if not exe:
        raise RuntimeError(f"{tool_name} was not found on PATH")
    return exe


def probe_audio(path: Path) -> AudioProbe:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if not is_supported_audio_file(path):
        raise ValueError(f"unsupported audio extension: {path.suffix}")

    ffprobe = require_ffmpeg_tool("ffprobe")
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    audio_stream = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"),
        {},
    )
    fmt = payload.get("format", {})
    duration = float(fmt.get("duration") or audio_stream.get("duration") or 0)
    size_bytes = int(fmt.get("size") or path.stat().st_size)
    sample_rate_raw = audio_stream.get("sample_rate")
    sample_rate = int(sample_rate_raw) if sample_rate_raw else None
    channels = audio_stream.get("channels")

    return AudioProbe(
        path=path,
        duration=duration,
        format_name=str(fmt.get("format_name") or path.suffix.lstrip(".")),
        sample_rate=sample_rate,
        channels=int(channels) if channels is not None else None,
        size_bytes=size_bytes,
    )
