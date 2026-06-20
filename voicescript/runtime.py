from __future__ import annotations

import io
import sys


class _NullTextStream(io.TextIOBase):
    encoding = "utf-8"

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        return len(str(value))

    def flush(self) -> None:
        return None


def ensure_std_streams() -> None:
    if sys.stdout is None:
        sys.stdout = _NullTextStream()
    if sys.stderr is None:
        sys.stderr = _NullTextStream()
