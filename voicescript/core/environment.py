from __future__ import annotations

import importlib.util
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolStatus:
    name: str
    available: bool
    path: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class PythonStatus:
    executable: str
    version: str
    supported: bool


@dataclass(frozen=True)
class TorchStatus:
    available: bool
    cuda_available: bool = False
    version: str = ""
    cuda_device: str = ""
    cuda_memory_gb: float | None = None
    detail: str = ""


@dataclass(frozen=True)
class EnvironmentReport:
    python: PythonStatus
    ffmpeg: ToolStatus
    ffprobe: ToolStatus
    torch: TorchStatus
    cache_dir: Path
    disk_free_bytes: int
    platform: str

    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.ffmpeg.available:
            warnings.append("ffmpeg was not found; audio decoding will fail.")
        if not self.ffprobe.available:
            warnings.append("ffprobe was not found; audio duration probing will fail.")
        if not self.torch.available:
            warnings.append("Torch is not installed; local ASR models cannot run yet.")
        elif not self.torch.cuda_available:
            warnings.append("CUDA is not available; large models will run on CPU and may be slow.")
        elif self.torch.cuda_memory_gb is not None and self.torch.cuda_memory_gb < 8:
            warnings.append("GPU memory is below 8GB; large models may need CPU fallback or low batch size.")
        return warnings


def _tool_status(name: str) -> ToolStatus:
    path = shutil.which(name)
    return ToolStatus(name=name, available=bool(path), path=path)


def _nearest_existing_path(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def _torch_status() -> TorchStatus:
    if importlib.util.find_spec("torch") is None:
        return TorchStatus(available=False, detail="torch import spec not found")
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        device = ""
        memory = None
        if cuda_available:
            device = torch.cuda.get_device_name(0)
            memory = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
        return TorchStatus(
            available=True,
            cuda_available=cuda_available,
            version=str(torch.__version__),
            cuda_device=device,
            cuda_memory_gb=memory,
        )
    except Exception as exc:  # pragma: no cover - defensive for broken installs
        return TorchStatus(available=False, detail=str(exc))


def check_environment(cache_dir: Path | None = None) -> EnvironmentReport:
    cache_dir = Path(cache_dir or Path.home() / ".cache" / "voicescript")
    disk_path = _nearest_existing_path(cache_dir)
    _, _, free = shutil.disk_usage(disk_path)
    version = ".".join(str(part) for part in sys.version_info[:3])
    return EnvironmentReport(
        python=PythonStatus(
            executable=sys.executable,
            version=version,
            supported=sys.version_info >= (3, 11),
        ),
        ffmpeg=_tool_status("ffmpeg"),
        ffprobe=_tool_status("ffprobe"),
        torch=_torch_status(),
        cache_dir=cache_dir,
        disk_free_bytes=free,
        platform=platform.platform(),
    )
