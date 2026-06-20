from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from huggingface_hub import snapshot_download

from voicescript.backends.base import TranscriptionProgress


def _default_whisper_dir() -> Path:
    default_cache = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return default_cache / "whisper"


def _format_mb(value: int) -> str:
    return f"{value / 1024 / 1024:.1f}MB"


def format_progress_units(current: int, total: int) -> str:
    if total < 1024 * 1024:
        return f"{current} / {total} files"
    return f"{_format_mb(current)} / {_format_mb(total)}"


def clean_invalid_whisper_checkpoint(
    model_id: str,
    *,
    model_dir: str | Path | None = None,
    progress: TranscriptionProgress | None = None,
) -> bool:
    cache_dir = Path(model_dir) if model_dir else _default_whisper_dir()
    checkpoint = cache_dir / f"{model_id}.pt"
    if checkpoint.exists() and checkpoint.is_file() and checkpoint.stat().st_size == 0:
        checkpoint.unlink()
        if progress:
            progress.emit(f"Removing incomplete Whisper checkpoint: {checkpoint}", 0.05)
        return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_whisper_checkpoint(
    whisper_module: Any,
    model_id: str,
    *,
    model_dir: str | Path | None = None,
    progress: TranscriptionProgress | None = None,
) -> Path | None:
    models = getattr(whisper_module, "_MODELS", None)
    if not isinstance(models, dict) or model_id not in models:
        return None

    cache_dir = Path(model_dir) if model_dir else _default_whisper_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = models[model_id]
    expected_sha256 = url.split("/")[-2]
    checkpoint = cache_dir / Path(urlparse(url).path).name

    clean_invalid_whisper_checkpoint(model_id, model_dir=cache_dir, progress=progress)
    if checkpoint.exists() and checkpoint.is_file() and checkpoint.stat().st_size > 0:
        if _sha256(checkpoint) == expected_sha256:
            if progress:
                progress.emit(f"Whisper {model_id} checkpoint is ready.", 0.08)
            return checkpoint
        if progress:
            progress.emit(f"Whisper {model_id} checkpoint checksum mismatch; re-downloading.", 0.08)

    if progress:
        progress.emit(f"Downloading Whisper {model_id} checkpoint.", 0.08)
    partial = checkpoint.with_suffix(f"{checkpoint.suffix}.part")
    try:
        with requests.get(url, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            last_emit = 0
            with partial.open("wb") as output:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    progress.raise_if_cancelled() if progress else None
                    if not block:
                        continue
                    output.write(block)
                    downloaded += len(block)
                    should_emit = downloaded == total or downloaded - last_emit >= 25 * 1024 * 1024
                    if progress and total and should_emit:
                        last_emit = downloaded
                        ratio = downloaded / total
                        progress.emit(
                            f"Downloading Whisper {model_id}: {format_progress_units(downloaded, total)}",
                            0.08 + min(0.17, ratio * 0.17),
                        )
            partial.replace(checkpoint)
    except Exception as exc:
        raise RuntimeError(f"Unable to download Whisper {model_id} checkpoint: {exc}") from exc

    if _sha256(checkpoint) != expected_sha256:
        raise RuntimeError(f"Downloaded Whisper {model_id} checkpoint failed SHA256 verification.")
    if progress:
        progress.emit(f"Whisper {model_id} checkpoint download complete.", 0.25)
    return checkpoint


def _make_progress_tqdm(progress: TranscriptionProgress, label: str, progress_value: float):
    from tqdm.auto import tqdm

    class VoiceScriptTqdm(tqdm):
        def update(self, n: int = 1):  # type: ignore[override]
            result = super().update(n)
            progress.raise_if_cancelled()
            if self.total:
                ratio = min(1.0, float(self.n) / float(self.total))
                progress.emit(
                    f"Downloading {label}: {format_progress_units(int(self.n), int(self.total))}",
                    min(0.9, progress_value + ratio * 0.2),
                )
            return result

    return VoiceScriptTqdm


def prefetch_huggingface_repo(
    repo_id: str,
    *,
    label: str,
    progress: TranscriptionProgress | None = None,
    progress_value: float = 0.1,
) -> Path:
    if progress:
        progress.emit(f"Checking/downloading {label}.", progress_value)
    try:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        path = snapshot_download(
            repo_id,
            max_workers=1,
            tqdm_class=_make_progress_tqdm(progress, label, progress_value) if progress else None,
        )
    except Exception as exc:
        raise RuntimeError(f"Unable to download or verify {label} from Hugging Face: {exc}") from exc
    if progress:
        progress.emit(f"{label} cache is ready.", min(0.9, progress_value + 0.2))
    return Path(path)
