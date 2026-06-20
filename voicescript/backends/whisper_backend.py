from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from typing import Any

from voicescript.core.audio import probe_audio, require_ffmpeg_tool
from voicescript.core.transcript import Segment, Transcript, Word

from .base import ASRBackend, BackendInfo, TranscriptionProgress


WHISPER_MODEL_KEY = "whisper-large-v3"
WHISPER_CHUNK_SECONDS = 60.0


def _word_from_mapping(raw_word: dict[str, Any]) -> Word:
    return Word(
        start=float(raw_word.get("start", 0.0)),
        end=float(raw_word.get("end", raw_word.get("start", 0.0))),
        text=str(raw_word.get("word", raw_word.get("text", ""))),
    )


def normalize_whisper_result(
    source: Path,
    duration: float,
    raw: dict[str, Any],
    *,
    offset: float = 0.0,
) -> Transcript:
    segments = []
    for raw_segment in raw.get("segments", []):
        words = [_word_from_mapping(word) for word in raw_segment.get("words", [])]
        segment = Segment(
            start=float(raw_segment.get("start", 0.0)),
            end=float(raw_segment.get("end", raw_segment.get("start", 0.0))),
            text=str(raw_segment.get("text", "")),
            words=words,
        )
        segments.append(segment.shifted(offset) if offset else segment)
    return Transcript(
        model=WHISPER_MODEL_KEY,
        source_file=Path(source),
        duration=float(duration) + offset,
        language=str(raw.get("language") or ""),
        segments=segments,
    )


def merge_whisper_chunk_results(source: Path, duration: float, chunks: list[Transcript]) -> Transcript:
    segments: list[Segment] = []
    languages: list[str] = []
    for chunk in chunks:
        segments.extend(chunk.segments)
        if chunk.language and chunk.language not in languages:
            languages.append(chunk.language)
    segments.sort(key=lambda item: (item.start, item.end))
    return Transcript(
        model=WHISPER_MODEL_KEY,
        source_file=Path(source),
        duration=float(duration),
        language=",".join(languages),
        segments=segments,
    )


def _transcribe_model(model: Any, audio_path: Path) -> dict[str, Any]:
    return model.transcribe(
        str(audio_path),
        task="transcribe",
        word_timestamps=True,
        verbose=False,
    )


class WhisperBackend(ASRBackend):
    info = BackendInfo(
        key=WHISPER_MODEL_KEY,
        label="Whisper large-v3",
        model_id="large-v3",
        needs_timestamps_model=False,
        notes="Official OpenAI Whisper large-v3 local model.",
    )

    def __init__(
        self,
        device: str | None = None,
        model_dir: str | None = None,
        chunk_seconds: float = WHISPER_CHUNK_SECONDS,
    ) -> None:
        self.device = device
        self.model_dir = model_dir
        self.chunk_seconds = float(chunk_seconds)
        self._model = None

    def _load_model(self, progress: TranscriptionProgress) -> Any:
        if self._model is not None:
            return self._model
        progress.emit("Loading Whisper large-v3", 0.05)
        import torch
        import whisper

        device = self.device or self._pick_device(torch, progress)
        self._model = whisper.load_model("large-v3", device=device, download_root=self.model_dir)
        return self._model

    def _pick_device(self, torch, progress: TranscriptionProgress) -> str:
        if not torch.cuda.is_available():
            return "cpu"
        total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        if total_gb < 10:
            progress.emit(
                "GPU memory is below Whisper large-v3 guidance; using CPU fallback.",
                0.06,
            )
            return "cpu"
        return "cuda"

    def transcribe(self, audio_path: Path, progress: TranscriptionProgress | None = None) -> Transcript:
        progress = progress or TranscriptionProgress()
        progress.raise_if_cancelled()
        audio = probe_audio(audio_path)
        model = self._load_model(progress)
        progress.raise_if_cancelled()

        if audio.duration <= self.chunk_seconds:
            progress.emit("Transcribing with Whisper large-v3", 0.2)
            raw = _transcribe_model(model, audio_path)
            progress.raise_if_cancelled()
            progress.emit("Formatting Whisper transcript", 0.95)
            return normalize_whisper_result(audio_path, audio.duration, raw)

        total_chunks = max(1, int((audio.duration + self.chunk_seconds - 0.001) // self.chunk_seconds))
        chunks: list[Transcript] = []
        with tempfile.TemporaryDirectory(prefix="voicescript-whisper-") as tmp:
            offset = 0.0
            index = 0
            while offset < audio.duration:
                progress.raise_if_cancelled()
                chunk_duration = min(self.chunk_seconds, audio.duration - offset)
                chunk_path = Path(tmp) / f"chunk_{index:04d}.wav"
                self._extract_chunk(audio_path, chunk_path, offset, chunk_duration)
                progress.emit(
                    f"Transcribing Whisper chunk {index + 1}/{total_chunks} at {offset:.1f}s",
                    min(0.9, 0.12 + (offset / max(audio.duration, 1.0)) * 0.78),
                )
                raw = _transcribe_model(model, chunk_path)
                chunks.append(
                    normalize_whisper_result(
                        audio_path,
                        chunk_duration,
                        raw,
                        offset=offset,
                    )
                )
                offset += chunk_duration
                index += 1
        progress.emit("Merging Whisper transcript chunks", 0.95)
        return merge_whisper_chunk_results(audio_path, audio.duration, chunks)

    def _extract_chunk(self, source: Path, target: Path, start: float, duration: float) -> None:
        ffmpeg = require_ffmpeg_tool("ffmpeg")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start:.3f}",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(target),
            ],
            check=True,
        )
