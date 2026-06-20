from __future__ import annotations

from pathlib import Path
from typing import Any

from voicescript.core.audio import probe_audio
from voicescript.core.transcript import Segment, Transcript, Word

from .base import ASRBackend, BackendInfo, TranscriptionProgress


WHISPER_MODEL_KEY = "whisper-large-v3"


def _word_from_mapping(raw_word: dict[str, Any]) -> Word:
    return Word(
        start=float(raw_word.get("start", 0.0)),
        end=float(raw_word.get("end", raw_word.get("start", 0.0))),
        text=str(raw_word.get("word", raw_word.get("text", ""))),
    )


def normalize_whisper_result(source: Path, duration: float, raw: dict[str, Any]) -> Transcript:
    segments = []
    for raw_segment in raw.get("segments", []):
        words = [_word_from_mapping(word) for word in raw_segment.get("words", [])]
        segments.append(
            Segment(
                start=float(raw_segment.get("start", 0.0)),
                end=float(raw_segment.get("end", raw_segment.get("start", 0.0))),
                text=str(raw_segment.get("text", "")),
                words=words,
            )
        )
    return Transcript(
        model=WHISPER_MODEL_KEY,
        source_file=Path(source),
        duration=float(duration),
        language=str(raw.get("language") or ""),
        segments=segments,
    )


class WhisperBackend(ASRBackend):
    info = BackendInfo(
        key=WHISPER_MODEL_KEY,
        label="Whisper large-v3",
        model_id="large-v3",
        needs_timestamps_model=False,
        notes="Official OpenAI Whisper large-v3 local model.",
    )

    def __init__(self, device: str | None = None, model_dir: str | None = None) -> None:
        self.device = device
        self.model_dir = model_dir
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
        progress.emit("Transcribing with Whisper large-v3", 0.2)
        raw = model.transcribe(
            str(audio_path),
            task="transcribe",
            word_timestamps=True,
            verbose=False,
        )
        progress.raise_if_cancelled()
        progress.emit("Formatting Whisper transcript", 0.95)
        return normalize_whisper_result(audio_path, audio.duration, raw)
