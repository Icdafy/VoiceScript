from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .transcript import Transcript


SUPPORTED_EXPORT_FORMATS = ("md", "txt", "srt", "json")


def format_clock(seconds: float, *, always_hours: bool = False, separator: str = ".") -> str:
    milliseconds = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    if always_hours or hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"
    return f"{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def format_srt_timestamp(seconds: float) -> str:
    return format_clock(seconds, always_hours=True, separator=",")


def transcript_to_txt(transcript: Transcript) -> str:
    return "".join(f"{segment.text}\n" for segment in transcript.segments if segment.text)


def transcript_to_markdown(transcript: Transcript) -> str:
    lines = [
        "# VoiceScript Transcript",
        "",
        f"- Source: `{transcript.source_file}`",
        f"- Model: `{transcript.model}`",
        f"- Language: `{transcript.language or 'unknown'}`",
        f"- Duration: `{format_clock(transcript.duration, always_hours=True)}`",
        "",
        "## Time Segments",
        "",
    ]
    for segment in transcript.segments:
        lines.append(
            f"[{format_clock(segment.start)} -> {format_clock(segment.end)}] {segment.text}"
        )
    return "\n".join(lines).rstrip() + "\n"


def transcript_to_srt(transcript: Transcript) -> str:
    blocks = []
    for index, segment in enumerate(transcript.segments, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
                    segment.text,
                ]
            )
        )
    return "\n\n".join(blocks).rstrip() + ("\n" if blocks else "")


def transcript_to_json(transcript: Transcript) -> str:
    return json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2) + "\n"


def export_transcript(
    transcript: Transcript,
    output_dir: Path,
    *,
    formats: Iterable[str] = SUPPORTED_EXPORT_FORMATS,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = transcript.source_file.stem or "transcript"
    writers = {
        "md": transcript_to_markdown,
        "txt": transcript_to_txt,
        "srt": transcript_to_srt,
        "json": transcript_to_json,
    }
    paths: dict[str, Path] = {}
    for fmt in formats:
        if fmt not in writers:
            raise ValueError(f"unsupported export format: {fmt}")
        path = output_dir / f"{stem}.{fmt}"
        path.write_text(writers[fmt](transcript), encoding="utf-8")
        paths[fmt] = path
    return paths
