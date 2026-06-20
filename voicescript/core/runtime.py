from __future__ import annotations

import sys
from typing import Any


class _NullStream:
    """A minimal writable stream used when sys.stdout/sys.stderr are None.

    PyInstaller windowed builds (console=False) set ``sys.stdout`` and
    ``sys.stderr`` to ``None``. Libraries such as Whisper and huggingface_hub
    print progress through ``tqdm``, which writes to these streams and crashes
    with ``'NoneType' object has no attribute 'write'``. Replacing the missing
    streams with this no-op writer keeps those libraries working.
    """

    encoding = "utf-8"

    def write(self, _data: Any = "") -> int:
        return 0

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        raise OSError("VoiceScript null stream has no file descriptor")


def ensure_std_streams() -> None:
    """Guarantee ``sys.stdout`` and ``sys.stderr`` are writable objects."""
    if getattr(sys, "stdout", None) is None:
        sys.stdout = _NullStream()
    if getattr(sys, "stderr", None) is None:
        sys.stderr = _NullStream()
