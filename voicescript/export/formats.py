from __future__ import annotations

import json
import re
from pathlib import Path

from voicescript.models import TranscriptDocument, TranscriptSegment

_PUNCTUATION_RE = re.compile(r"[，。！？；：、,.!?;:]")


def _maybe_strip_punctuation(text: str, restore_punctuation: bool) -> str:
    if restore_punctuation:
        return text
    return _PUNCTUATION_RE.sub("", text)


def format_timestamp(seconds: float, srt: bool = False) -> str:
    ms_total = int(round(float(seconds) * 1000))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    sec, ms = divmod(rem, 1000)
    sep = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{sec:02d}{sep}{ms:03d}"


def _segment_text(segment: TranscriptSegment, restore_punctuation: bool) -> str:
    return _maybe_strip_punctuation(segment.text, restore_punctuation)


def export_txt(doc: TranscriptDocument, restore_punctuation: bool = True) -> str:
    lines = []
    for segment in doc.segments:
        text = _segment_text(segment, restore_punctuation)
        lines.append(
            f"[{format_timestamp(segment.start_sec)} - {format_timestamp(segment.end_sec)}] {text}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def export_markdown(doc: TranscriptDocument, restore_punctuation: bool = True) -> str:
    lines = [
        f"# {doc.source_file.stem}",
        "",
        f"- Source: `{doc.source_file}`",
        f"- Model: `{doc.model}`",
        f"- Language: `{doc.language or 'auto'}`",
        "",
        "| # | Start | End | Text |",
        "|---:|---|---|---|",
    ]
    for segment in doc.segments:
        text = _segment_text(segment, restore_punctuation).replace("|", "\\|")
        lines.append(
            f"| {segment.index} | {format_timestamp(segment.start_sec)} | "
            f"{format_timestamp(segment.end_sec)} | {text} |"
        )
    return "\n".join(lines) + "\n"


def export_srt(doc: TranscriptDocument, restore_punctuation: bool = True) -> str:
    blocks = []
    for segment in doc.segments:
        text = _segment_text(segment, restore_punctuation)
        blocks.append(
            "\n".join(
                [
                    str(segment.index),
                    f"{format_timestamp(segment.start_sec, srt=True)} --> {format_timestamp(segment.end_sec, srt=True)}",
                    text,
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def export_json(doc: TranscriptDocument, restore_punctuation: bool = True) -> str:
    payload = doc.to_dict()
    if not restore_punctuation:
        for segment in payload["segments"]:
            segment["text"] = _maybe_strip_punctuation(segment["text"], False)
        payload["text"] = "\n".join(segment["text"] for segment in payload["segments"] if segment["text"])
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


EXPORTERS = {
    "txt": export_txt,
    "md": export_markdown,
    "markdown": export_markdown,
    "srt": export_srt,
    "json": export_json,
}


def normalize_formats(formats: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in formats:
        value = str(item).strip().lower()
        if value == "all":
            return ("txt", "md", "srt", "json")
        if value == "markdown":
            value = "md"
        if value not in EXPORTERS:
            raise ValueError(f"unsupported output format: {item}")
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized or ["txt"])


def write_exports(
    doc: TranscriptDocument,
    output_dir: Path,
    formats: tuple[str, ...],
    restore_punctuation: bool = True,
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in normalize_formats(formats):
        ext = "md" if fmt == "markdown" else fmt
        path = output_dir / f"{doc.source_file.stem}.{ext}"
        exporter = EXPORTERS[fmt]
        path.write_text(exporter(doc, restore_punctuation), encoding="utf-8")
        written.append(path)
    return written
