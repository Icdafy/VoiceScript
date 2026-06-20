from __future__ import annotations

import argparse
import json
from pathlib import Path

from voicescript.backends.base import TranscriptionProgress
from voicescript.backends.qwen_backend import QWEN_MODEL_KEY, QwenBackend
from voicescript.backends.whisper_backend import WHISPER_MODEL_KEY, WhisperBackend
from voicescript.core.environment import check_environment
from voicescript.core.exporters import SUPPORTED_EXPORT_FORMATS, export_transcript
from voicescript.core.settings import default_settings


MODEL_CHOICES = (WHISPER_MODEL_KEY, QWEN_MODEL_KEY)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voicescript")
    subparsers = parser.add_subparsers(dest="command", required=True)

    env_parser = subparsers.add_parser("env", help="check local runtime environment")
    env_parser.add_argument("--cache-dir", type=Path, default=None)

    transcribe = subparsers.add_parser("transcribe", help="transcribe one uploaded audio file")
    transcribe.add_argument("--model", choices=MODEL_CHOICES, required=True)
    transcribe.add_argument("--input", type=Path, required=True)
    transcribe.add_argument("--out", type=Path, required=True)
    transcribe.add_argument(
        "--formats",
        default="md,txt,srt,json",
        help="comma-separated export formats: md,txt,srt,json",
    )
    transcribe.add_argument("--obsidian", action="store_true", help="also export markdown to Obsidian")
    transcribe.add_argument("--obsidian-dir", type=Path, default=None)
    return parser


def select_backend(model_key: str):
    if model_key == WHISPER_MODEL_KEY:
        return WhisperBackend()
    if model_key == QWEN_MODEL_KEY:
        return QwenBackend()
    raise ValueError(f"unknown model: {model_key}")


def _parse_formats(raw: str) -> tuple[str, ...]:
    formats = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    unsupported = [fmt for fmt in formats if fmt not in SUPPORTED_EXPORT_FORMATS]
    if unsupported:
        raise ValueError(f"unsupported export formats: {', '.join(unsupported)}")
    return formats


def run_transcribe_command(args, *, backend=None) -> dict[str, Path]:
    backend = backend or select_backend(args.model)
    progress = TranscriptionProgress(callback=lambda message, value=None: print(message))
    transcript = backend.transcribe(Path(args.input), progress=progress)
    paths = export_transcript(transcript, Path(args.out), formats=_parse_formats(args.formats))
    if getattr(args, "obsidian", False):
        settings = default_settings()
        obsidian_dir = Path(args.obsidian_dir or settings.obsidian_dir)
        export_transcript(transcript, obsidian_dir, formats=("md", "json"))
    return paths


def run_env_command(args) -> int:
    report = check_environment(cache_dir=args.cache_dir)
    print(json.dumps(_environment_to_dict(report), ensure_ascii=False, indent=2))
    return 0


def _environment_to_dict(report) -> dict:
    return {
        "python": report.python.__dict__,
        "ffmpeg": report.ffmpeg.__dict__,
        "ffprobe": report.ffprobe.__dict__,
        "torch": report.torch.__dict__,
        "cache_dir": str(report.cache_dir),
        "disk_free_bytes": report.disk_free_bytes,
        "platform": report.platform,
        "warnings": report.warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "env":
        return run_env_command(args)
    if args.command == "transcribe":
        paths = run_transcribe_command(args)
        for fmt, path in paths.items():
            print(f"{fmt}: {path}")
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
