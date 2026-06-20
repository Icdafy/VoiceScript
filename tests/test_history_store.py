from pathlib import Path

from voicescript.history import RecentFile, RecentFileStore


def test_recent_file_store_persists_latest_items_first(tmp_path):
    store_path = tmp_path / "recent.json"
    store = RecentFileStore(store_path, limit=2)

    store.add(
        RecentFile(
            file_path=Path("a.m4a"),
            duration_label="00:00:01",
            size_label="1 KB",
            transcribed_at="2026-06-20 21:00",
            status="已完成",
            output_dir=Path("out-a"),
        )
    )
    store.add(
        RecentFile(
            file_path=Path("b.amr"),
            duration_label="00:00:02",
            size_label="2 KB",
            transcribed_at="2026-06-20 21:01",
            status="已完成",
            output_dir=Path("out-b"),
        )
    )
    store.add(
        RecentFile(
            file_path=Path("c.wav"),
            duration_label="00:00:03",
            size_label="3 KB",
            transcribed_at="2026-06-20 21:02",
            status="失败",
            output_dir=Path("out-c"),
        )
    )

    loaded = RecentFileStore(store_path, limit=2).load()

    assert [item.file_path.name for item in loaded] == ["c.wav", "b.amr"]
    assert loaded[0].status == "失败"
