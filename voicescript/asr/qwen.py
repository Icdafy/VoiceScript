from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys
import types
from typing import Any

from voicescript.audio.probe import probe_audio
from voicescript.models import ProgressCallback, TranscriptionJobConfig, TranscriptDocument, TranscriptSegment


class QwenModelProfile(str, Enum):
    STANDARD = "standard"
    PRECISE = "precise"

    @classmethod
    def default(cls) -> "QwenModelProfile":
        return cls.STANDARD


@dataclass(frozen=True)
class QwenProfileConfig:
    label: str
    asr_checkpoint: str
    aligner_checkpoint: str
    max_new_tokens: int
    max_inference_batch_size: int


MODEL_PROFILES = {
    QwenModelProfile.STANDARD: QwenProfileConfig(
        label="标准模型",
        asr_checkpoint="Qwen/Qwen3-ASR-0.6B",
        aligner_checkpoint="Qwen/Qwen3-ForcedAligner-0.6B",
        max_new_tokens=512,
        max_inference_batch_size=8,
    ),
    QwenModelProfile.PRECISE: QwenProfileConfig(
        label="精准模型",
        asr_checkpoint="Qwen/Qwen3-ASR-1.7B",
        aligner_checkpoint="Qwen/Qwen3-ForcedAligner-0.6B",
        max_new_tokens=768,
        max_inference_batch_size=4,
    ),
}


def prepare_qwen_runtime() -> None:
    """Work around nagisa/DyNet model loading failures under non-ASCII Windows paths."""
    try:
        import nagisa  # noqa: F401
        return
    except Exception:
        for name in list(sys.modules):
            if name == "nagisa" or name.startswith("nagisa."):
                sys.modules.pop(name, None)

    shim = types.ModuleType("nagisa")

    class _Token:
        def __init__(self, text: str) -> None:
            self.words = [char for char in str(text) if char.strip()]

    def tagging(text: str):
        return _Token(text)

    shim.tagging = tagging  # type: ignore[attr-defined]
    shim.__version__ = "0.2.11-voicescript-shim"  # type: ignore[attr-defined]
    sys.modules["nagisa"] = shim


def normalize_profile(value: str | QwenModelProfile | None) -> QwenModelProfile:
    if isinstance(value, QwenModelProfile):
        return value
    if not value:
        return QwenModelProfile.default()
    lowered = str(value).strip().lower()
    if lowered in {"standard", "标准模型", "标准"}:
        return QwenModelProfile.STANDARD
    if lowered in {"precise", "精准模型", "高精度", "精确"}:
        return QwenModelProfile.PRECISE
    raise ValueError(f"unsupported Qwen model profile: {value}")


def _qwen_language(language: str | None) -> str | None:
    if language is None:
        return None
    value = str(language).strip()
    if value.lower() in {"", "auto", "自动识别"}:
        return None
    mapping = {
        "中文": "Chinese",
        "中文（普通话）": "Chinese",
        "普通话": "Chinese",
        "english": "English",
        "英文": "English",
        "cantonese": "Cantonese",
        "粤语": "Cantonese",
    }
    return mapping.get(value.lower(), mapping.get(value, value))


def _item_attr(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _segments_from_timestamps(items: list[Any], fallback_text: str, duration_sec: float) -> list[TranscriptSegment]:
    if not items:
        return [TranscriptSegment(index=1, start_sec=0.0, end_sec=duration_sec, text=fallback_text)]

    segments: list[TranscriptSegment] = []
    buffer: list[str] = []
    start = float(_item_attr(items[0], "start_time", "start", default=0.0) or 0.0)
    end = start
    for item in items:
        text = str(_item_attr(item, "text", default="") or "")
        item_start = float(_item_attr(item, "start_time", "start", default=end) or end)
        item_end = float(_item_attr(item, "end_time", "end", default=item_start) or item_start)
        if not buffer:
            start = item_start
        buffer.append(text)
        end = item_end
        joined = "".join(buffer).strip()
        should_flush = joined.endswith(("。", "！", "？", ".", "!", "?")) or (end - start) >= 18
        if should_flush and joined:
            segment_end = duration_sec if end <= start and duration_sec > start else end
            segments.append(
                TranscriptSegment(index=len(segments) + 1, start_sec=start, end_sec=segment_end, text=joined)
            )
            buffer = []
    if buffer:
        joined = "".join(buffer).strip()
        if joined:
            segment_end = duration_sec if end <= start and duration_sec > start else end
            segments.append(TranscriptSegment(index=len(segments) + 1, start_sec=start, end_sec=segment_end, text=joined))
    return segments or [TranscriptSegment(index=1, start_sec=0.0, end_sec=duration_sec, text=fallback_text)]


class QwenAsrBackend:
    def __init__(self, profile: str | QwenModelProfile | None = None) -> None:
        self.profile = normalize_profile(profile)
        self.profile_config = MODEL_PROFILES[self.profile]
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        prepare_qwen_runtime()
        import torch
        from qwen_asr import Qwen3ASRModel

        use_cuda = bool(torch.cuda.is_available())
        dtype = torch.bfloat16 if use_cuda else torch.float32
        device_map = "cuda:0" if use_cuda else "cpu"
        kwargs = {
            "dtype": dtype,
            "device_map": device_map,
            "max_inference_batch_size": self.profile_config.max_inference_batch_size,
            "max_new_tokens": self.profile_config.max_new_tokens,
            "forced_aligner": self.profile_config.aligner_checkpoint,
            "forced_aligner_kwargs": {
                "dtype": dtype,
                "device_map": device_map,
            },
        }
        self._model = Qwen3ASRModel.from_pretrained(self.profile_config.asr_checkpoint, **kwargs)
        return self._model

    def transcribe(
        self,
        config: TranscriptionJobConfig,
        progress_callback: ProgressCallback | None = None,
    ) -> TranscriptDocument:
        input_file = Path(config.input_file)
        if progress_callback:
            progress_callback(0.05, "检查音频文件")
        audio_info = probe_audio(input_file)

        if progress_callback:
            progress_callback(0.15, "加载 Qwen3-ASR 模型")
        model = self._load_model()

        if progress_callback:
            progress_callback(0.35, "开始语音识别")
        result = model.transcribe(
            audio=str(input_file),
            language=_qwen_language(config.language),
            return_time_stamps=True,
        )[0]

        if progress_callback:
            progress_callback(0.9, "生成时间分段")
        language = str(_item_attr(result, "language", default=config.language or "") or "")
        text = str(_item_attr(result, "text", default="") or "")
        timestamps = list(_item_attr(result, "time_stamps", default=[]) or [])
        segments = _segments_from_timestamps(timestamps, text, audio_info.duration_sec)
        if progress_callback:
            progress_callback(1.0, "转录完成")
        return TranscriptDocument(
            source_file=input_file,
            duration_sec=audio_info.duration_sec,
            language=language,
            model=self.profile_config.asr_checkpoint,
            segments=segments,
        )
