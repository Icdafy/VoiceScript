from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecentFile:
    file_path: Path
    duration_label: str
    size_label: str
    transcribed_at: str
    status: str
    output_dir: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "file_path": str(self.file_path),
            "duration_label": self.duration_label,
            "size_label": self.size_label,
            "transcribed_at": self.transcribed_at,
            "status": self.status,
            "output_dir": str(self.output_dir),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "RecentFile":
        return cls(
            file_path=Path(payload["file_path"]),
            duration_label=str(payload.get("duration_label") or ""),
            size_label=str(payload.get("size_label") or ""),
            transcribed_at=str(payload.get("transcribed_at") or ""),
            status=str(payload.get("status") or ""),
            output_dir=Path(payload.get("output_dir") or "."),
        )


class RecentFileStore:
    def __init__(self, path: Path, limit: int = 20) -> None:
        self.path = Path(path)
        self.limit = limit

    def load(self) -> list[RecentFile]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [RecentFile.from_dict(item) for item in payload[: self.limit]]

    def save(self, items: list[RecentFile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in items[: self.limit]]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, item: RecentFile) -> None:
        existing = [old for old in self.load() if old.file_path != item.file_path]
        self.save([item, *existing])
