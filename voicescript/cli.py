from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from voicescript import __version__
from voicescript.asr.mock import MockAsrBackend
from voicescript.asr.qwen import QwenAsrBackend, normalize_profile
from voicescript.audio.probe import SUPPORTED_AUDIO_EXTENSIONS, probe_audio
from voicescript.export.formats import normalize_formats, write_exports
from voicescript.models import TranscriptionJobConfig
from voicescript.runtime import ensure_std_streams


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voicescript")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("env", help="check local runtime")

    transcribe = subparsers.add_parser("transcribe", help="transcribe an audio file")
    transcribe.add_argument("--input", required=True, type=Path)
    transcribe.add_argument("--out", required=True, type=Path)
    transcribe.add_argument("--formats", default="txt")
    transcribe.add_argument("--model", default="standard", choices=["standard", "precise"])
    transcribe.add_argument("--language", default="auto")
    transcribe.add_argument("--no-punctuation", action="store_true")
    return parser


def _run_env() -> int:
    print(f"VoiceScript {__version__}")
    print(f"Python {sys.version.split()[0]}")
    print(f"ffmpeg: {shutil.which('ffmpeg') or 'missing'}")
    print(f"ffprobe: {shutil.which('ffprobe') or 'missing'}")
    print("Supported:", ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS)))
    return 0


def _backend(model: str):
    if os.environ.get("VOICESCRIPT_USE_MOCK_ASR") == "1":
        return MockAsrBackend()
    return QwenAsrBackend(normalize_profile(model))


def _run_transcribe(args: argparse.Namespace) -> int:
    audio = probe_audio(args.input)
    formats = normalize_formats(tuple(part.strip() for part in args.formats.split(",")))
    config = TranscriptionJobConfig(
        input_file=audio.path,
        language=args.language,
        model_profile=args.model,
        output_dir=args.out,
        output_formats=formats,
        restore_punctuation=not args.no_punctuation,
    )
    backend = _backend(args.model)
    doc = backend.transcribe(config, lambda value, message: print(f"{value:.0%} {message}"))
    written = write_exports(doc, config.output_dir, formats, config.restore_punctuation)
    for path in written:
        print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    ensure_std_streams()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "env":
        return _run_env()
    if args.command == "transcribe":
        return _run_transcribe(args)
    parser.error(f"unknown command: {args.command}")
    return 2
