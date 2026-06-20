from __future__ import annotations

import math
import shutil
import sys
import tempfile
import types
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from voicescript.audio.probe import extract_segment_wav, probe_audio
from voicescript.models import ProgressCallback, TranscriptionJobConfig, TranscriptDocument, TranscriptSegment

# 每段转录的时长（秒）。长音频按 30 分钟切片，逐段送入 Qwen3-ASR，
# 既能给出细粒度进度，又能稳定转录数小时的录音。
SEGMENT_SECONDS = 30 * 60


def _format_clock(seconds: float) -> str:
    total = int(round(max(0.0, float(seconds))))
    hours, rem = divmod(total, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{sec:02d}"


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


def _segments_from_timestamps(
    items: list[Any],
    fallback_text: str,
    duration_sec: float,
    time_offset: float = 0.0,
    start_index: int = 1,
) -> list[TranscriptSegment]:
    if not items:
        return [
            TranscriptSegment(
                index=start_index,
                start_sec=time_offset,
                end_sec=time_offset + duration_sec,
                text=fallback_text,
            )
        ]

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
                TranscriptSegment(
                    index=start_index + len(segments),
                    start_sec=time_offset + start,
                    end_sec=time_offset + segment_end,
                    text=joined,
                )
            )
            buffer = []
    if buffer:
        joined = "".join(buffer).strip()
        if joined:
            segment_end = duration_sec if end <= start and duration_sec > start else end
            segments.append(
                TranscriptSegment(
                    index=start_index + len(segments),
                    start_sec=time_offset + start,
                    end_sec=time_offset + segment_end,
                    text=joined,
                )
            )
    return segments or [
        TranscriptSegment(
            index=start_index,
            start_sec=time_offset,
            end_sec=time_offset + duration_sec,
            text=fallback_text,
        )
    ]


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

        def emit(value: float, message: str) -> None:
            if progress_callback:
                progress_callback(value, message)

        emit(0.02, "检查音频文件…")
        audio_info = probe_audio(input_file)
        duration = float(audio_info.duration_sec or 0.0)
        total_label = _format_clock(duration)

        # 默认以中文输出为主：未指定或自动识别时强制中文。
        language = _qwen_language(config.language) or "Chinese"

        n_segments = max(1, math.ceil(duration / SEGMENT_SECONDS)) if duration > 0 else 1
        plan = "整段转录" if n_segments == 1 else f"将按 30 分钟切成 {n_segments} 段转录"
        emit(0.04, f"音频时长 {total_label}，{plan}…")

        emit(0.08, "加载 Qwen3-ASR 模型（首次使用需下载模型，请耐心等待）…")
        model = self._load_model()
        emit(0.1, f"模型就绪，输出语言：{language}")

        work_dir = Path(tempfile.mkdtemp(prefix="voicescript_seg_"))
        merged: list[TranscriptSegment] = []
        detected_languages: list[str] = []
        try:
            for index in range(n_segments):
                seg_start = index * SEGMENT_SECONDS
                seg_end = min(duration, seg_start + SEGMENT_SECONDS) if duration > 0 else 0.0
                seg_duration = (seg_end - seg_start) if duration > 0 else None
                span = f"{_format_clock(seg_start)} – {_format_clock(seg_end)}" if duration > 0 else "整段"

                emit(
                    0.1 + 0.85 * (index / n_segments),
                    f"正在转录第 {index + 1}/{n_segments} 段（{span}）· 提取音频片段…",
                )
                segment_wav = work_dir / f"segment_{index:03d}.wav"
                extract_segment_wav(input_file, segment_wav, seg_start, seg_duration)

                emit(
                    0.1 + 0.85 * (index / n_segments) + 0.02,
                    f"正在转录第 {index + 1}/{n_segments} 段（{span}）· Qwen3-ASR 识别中…",
                )
                result = model.transcribe(
                    audio=str(segment_wav),
                    language=language,
                    return_time_stamps=True,
                )[0]

                seg_language = str(_item_attr(result, "language", default="") or "")
                if seg_language:
                    detected_languages.append(seg_language)
                text = str(_item_attr(result, "text", default="") or "")
                timestamps = list(_item_attr(result, "time_stamps", default=[]) or [])
                merged.extend(
                    _segments_from_timestamps(
                        timestamps,
                        text,
                        seg_duration if seg_duration is not None else duration,
                        time_offset=seg_start,
                        start_index=len(merged) + 1,
                    )
                )
                emit(
                    0.1 + 0.85 * ((index + 1) / n_segments),
                    f"第 {index + 1}/{n_segments} 段完成 · 已转录 {_format_clock(seg_end)}/{total_label}"
                    f" · 累计 {len(merged)} 条片段",
                )
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        emit(0.97, "合并时间分段，生成转录文本…")
        segments = [
            TranscriptSegment(index=i + 1, start_sec=s.start_sec, end_sec=s.end_sec, text=s.text)
            for i, s in enumerate(merged)
            if s.text
        ]
        if not segments:
            segments = [TranscriptSegment(index=1, start_sec=0.0, end_sec=duration, text="")]

        emit(1.0, f"转录完成 · 共 {len(segments)} 条片段 · 时长 {total_label}")
        return TranscriptDocument(
            source_file=input_file,
            duration_sec=audio_info.duration_sec,
            language=detected_languages[0] if detected_languages else language,
            model=self.profile_config.asr_checkpoint,
            segments=segments,
        )
