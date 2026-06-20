from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_AUDIO_EXTENSIONS = {
    ".m4a",
    ".aac",
    ".caf",
    ".amr",
    ".3gp",
    ".ogg",
    ".opus",
    ".mp3",
    ".wav",
    ".flac",
}


@dataclass(frozen=True)
class AudioInfo:
    path: Path
    duration_sec: float
    size_bytes: int
    format_name: str = ""


def is_supported_audio_file(path: Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def build_ffprobe_command(input_file: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_file),
    ]


def build_ffmpeg_command(input_file: Path, output_file: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        str(output_file),
    ]


def build_segment_command(
    input_file: Path,
    output_file: Path,
    start_sec: float = 0.0,
    duration_sec: float | None = None,
) -> list[str]:
    """ffmpeg command to extract a mono 16kHz wav slice [start, start+duration)."""
    command = ["ffmpeg", "-y"]
    if start_sec and start_sec > 0:
        command += ["-ss", f"{float(start_sec):.3f}"]
    command += ["-i", str(input_file), "-vn", "-ac", "1", "-ar", "16000", "-sample_fmt", "s16"]
    if duration_sec is not None and duration_sec > 0:
        command += ["-t", f"{float(duration_sec):.3f}"]
    command.append(str(output_file))
    return command


def extract_segment_wav(
    input_file: Path,
    output_file: Path,
    start_sec: float = 0.0,
    duration_sec: float | None = None,
) -> Path:
    """Extract a mono 16kHz wav slice, converting any supported format to wav."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        build_segment_command(Path(input_file), output_file, start_sec, duration_sec),
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return output_file


def probe_audio(path: Path) -> AudioInfo:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if not is_supported_audio_file(path):
        raise ValueError(f"unsupported audio extension: {path.suffix}")

    result = subprocess.run(
        build_ffprobe_command(path),
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(result.stdout or "{}")
    fmt = payload.get("format", {})
    duration = float(fmt.get("duration") or 0.0)
    return AudioInfo(
        path=path,
        duration_sec=round(duration, 3),
        size_bytes=path.stat().st_size,
        format_name=str(fmt.get("format_name") or ""),
    )


def transcode_to_wav(input_file: Path, output_file: Path) -> Path:
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        build_ffmpeg_command(Path(input_file), output_file),
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return output_file
