from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import sys
import types
from typing import Any, Iterable

from voicescript.core.audio import probe_audio, require_ffmpeg_tool
from voicescript.core.model_cache import prefetch_huggingface_repo
from voicescript.core.transcript import Segment, Transcript, Word

from .base import ASRBackend, BackendInfo, TranscriptionProgress


QWEN_MODEL_KEY = "qwen3-asr-1.7b"
QWEN_MODEL_ID = "Qwen/Qwen3-ASR-1.7B"
QWEN_ALIGNER_ID = "Qwen/Qwen3-ForcedAligner-0.6B"
QWEN_CHUNK_SECONDS = 170.0


def install_nagisa_import_fallback(*, force: bool = False) -> bool:
    """Install a minimal nagisa module when DyNet cannot read data under Unicode paths.

    Qwen's forced aligner imports nagisa at module import time. On some Windows
    installs, DyNet fails to read nagisa's model file when the virtualenv path
    contains non-ASCII characters. Chinese and English alignment do not need
    nagisa; Japanese tokenization can still fall back to a conservative splitter.
    """
    if not force:
        try:
            import nagisa  # noqa: F401

            return False
        except Exception:
            for name in list(sys.modules):
                if name == "nagisa" or name.startswith("nagisa."):
                    sys.modules.pop(name, None)

    module = types.ModuleType("nagisa")

    def tagging(text: str):
        raw = str(text or "").strip()
        words = raw.split() if " " in raw else ([raw] if raw else [])
        return types.SimpleNamespace(words=words)

    module.tagging = tagging
    module.__version__ = "fallback"
    sys.modules["nagisa"] = module
    return True


def _import_qwen_model_class():
    install_nagisa_import_fallback()
    try:
        from qwen_asr import Qwen3ASRModel

        return Qwen3ASRModel
    except Exception as exc:
        if "nagisa" not in str(exc).lower() and "dynet" not in str(exc).lower():
            raise
        install_nagisa_import_fallback(force=True)
        for name in list(sys.modules):
            if name == "qwen_asr" or name.startswith("qwen_asr."):
                sys.modules.pop(name, None)
        from qwen_asr import Qwen3ASRModel

        return Qwen3ASRModel


def _iter_timestamp_items(raw_items: Any) -> Iterable[Any]:
    if raw_items is None:
        return []
    if hasattr(raw_items, "items") and not isinstance(raw_items, list):
        return raw_items.items
    return raw_items


def normalize_qwen_result(
    source: Path,
    duration: float,
    raw: Any,
    *,
    offset: float = 0.0,
) -> Transcript:
    text = str(getattr(raw, "text", "") or "").strip()
    language = str(getattr(raw, "language", "") or "")
    words: list[Word] = []
    timestamp_items = list(_iter_timestamp_items(getattr(raw, "time_stamps", None)))
    for item in timestamp_items:
        start = float(getattr(item, "start_time", 0.0)) + offset
        end = float(getattr(item, "end_time", start)) + offset
        words.append(Word(start=start, end=end, text=str(getattr(item, "text", ""))))

    if words:
        start = min(word.start for word in words)
        end = max(word.end for word in words)
    else:
        start = offset
        end = offset + float(duration)

    segment = Segment(start=start, end=end, text=text, words=words)
    return Transcript(
        model=QWEN_MODEL_KEY,
        source_file=Path(source),
        duration=offset + float(duration),
        language=language,
        segments=[segment] if text or words else [],
    )


def merge_qwen_chunk_results(source: Path, duration: float, chunks: list[Transcript]) -> Transcript:
    segments: list[Segment] = []
    languages: list[str] = []
    for chunk in chunks:
        segments.extend(chunk.segments)
        if chunk.language and chunk.language not in languages:
            languages.append(chunk.language)
    segments.sort(key=lambda item: (item.start, item.end))
    return Transcript(
        model=QWEN_MODEL_KEY,
        source_file=Path(source),
        duration=float(duration),
        language=",".join(languages),
        segments=segments,
    )


class QwenBackend(ASRBackend):
    info = BackendInfo(
        key=QWEN_MODEL_KEY,
        label="Qwen3-ASR-1.7B",
        model_id=QWEN_MODEL_ID,
        needs_timestamps_model=True,
        notes="Qwen3-ASR with Qwen3 ForcedAligner timestamps.",
    )

    def __init__(
        self,
        device_map: str | None = None,
        dtype_name: str = "auto",
        max_inference_batch_size: int = 1,
        max_new_tokens: int = 1024,
    ) -> None:
        self.device_map = device_map
        self.dtype_name = dtype_name
        self.max_inference_batch_size = max_inference_batch_size
        self.max_new_tokens = max_new_tokens
        self._model = None

    def _load_model(self, progress: TranscriptionProgress) -> Any:
        if self._model is not None:
            return self._model
        progress.emit("Preparing Qwen3-ASR-1.7B and forced aligner", 0.05)
        import torch

        prefetch_huggingface_repo(
            QWEN_MODEL_ID,
            label="Qwen3-ASR-1.7B",
            progress=progress,
            progress_value=0.08,
        )
        prefetch_huggingface_repo(
            QWEN_ALIGNER_ID,
            label="Qwen3-ForcedAligner-0.6B",
            progress=progress,
            progress_value=0.3,
        )
        progress.emit("Loading Qwen3-ASR-1.7B and forced aligner into memory", 0.55)
        Qwen3ASRModel = _import_qwen_model_class()

        device_map = self.device_map or self._pick_device_map(torch, progress)
        if self.dtype_name == "auto":
            dtype = torch.bfloat16 if device_map != "cpu" else torch.float32
        else:
            dtype = getattr(torch, self.dtype_name)
        self._model = Qwen3ASRModel.from_pretrained(
            QWEN_MODEL_ID,
            dtype=dtype,
            device_map=device_map,
            forced_aligner=QWEN_ALIGNER_ID,
            forced_aligner_kwargs={"dtype": dtype, "device_map": device_map},
            max_inference_batch_size=self.max_inference_batch_size,
            max_new_tokens=self.max_new_tokens,
        )
        return self._model

    def _pick_device_map(self, torch, progress: TranscriptionProgress) -> str:
        if not torch.cuda.is_available():
            return "cpu"
        total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        if total_gb < 8:
            progress.emit(
                "GPU memory is below Qwen timestamp guidance; using CPU fallback.",
                0.06,
            )
            return "cpu"
        return "cuda:0"

    def transcribe(self, audio_path: Path, progress: TranscriptionProgress | None = None) -> Transcript:
        progress = progress or TranscriptionProgress()
        progress.raise_if_cancelled()
        audio = probe_audio(audio_path)
        model = self._load_model(progress)
        progress.raise_if_cancelled()
        if audio.duration <= QWEN_CHUNK_SECONDS:
            return self._transcribe_one(model, audio_path, audio.duration, 0.0, progress)

        chunks: list[Transcript] = []
        with tempfile.TemporaryDirectory(prefix="voicescript-qwen-") as tmp:
            offset = 0.0
            index = 0
            while offset < audio.duration:
                progress.raise_if_cancelled()
                chunk_duration = min(QWEN_CHUNK_SECONDS, audio.duration - offset)
                chunk_path = Path(tmp) / f"chunk_{index:04d}.wav"
                self._extract_chunk(audio_path, chunk_path, offset, chunk_duration)
                progress.emit(
                    f"Transcribing Qwen chunk {index + 1} at {offset:.1f}s",
                    min(0.9, 0.15 + (offset / max(audio.duration, 1.0)) * 0.75),
                )
                chunks.append(self._transcribe_one(model, chunk_path, chunk_duration, offset, progress))
                offset += chunk_duration
                index += 1
        progress.emit("Merging Qwen transcript chunks", 0.95)
        return merge_qwen_chunk_results(audio_path, audio.duration, chunks)

    def _transcribe_one(
        self,
        model: Any,
        audio_path: Path,
        duration: float,
        offset: float,
        progress: TranscriptionProgress,
    ) -> Transcript:
        progress.emit("Transcribing with Qwen3-ASR-1.7B", 0.65 if offset == 0 else None)
        results = model.transcribe(
            audio=str(audio_path),
            language=None,
            return_time_stamps=True,
        )
        progress.raise_if_cancelled()
        if not results:
            return Transcript(QWEN_MODEL_KEY, Path(audio_path), duration, "", [])
        return normalize_qwen_result(audio_path, duration, results[0], offset=offset)

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
