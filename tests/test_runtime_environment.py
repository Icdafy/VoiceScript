import sys

from voicescript.environment import collect_environment
from voicescript.runtime import ensure_std_streams


def test_ensure_std_streams_replaces_none_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    ensure_std_streams()

    assert sys.stdout is not None
    assert sys.stderr is not None
    assert sys.stderr.write("safe") == 4


def test_collect_environment_reports_required_tools():
    report = collect_environment()

    assert "python" in report
    assert "ffmpeg" in report
    assert "ffprobe" in report
