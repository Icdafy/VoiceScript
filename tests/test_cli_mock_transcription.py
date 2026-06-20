import wave
from pathlib import Path

from voicescript.cli import main


def _write_silence(path: Path) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 16000)


def test_cli_transcribe_with_mock_backend_exports_selected_formats(tmp_path, monkeypatch):
    audio_file = tmp_path / "sample.wav"
    output_dir = tmp_path / "out"
    _write_silence(audio_file)
    monkeypatch.setenv("VOICESCRIPT_USE_MOCK_ASR", "1")

    exit_code = main(
        [
            "transcribe",
            "--input",
            str(audio_file),
            "--out",
            str(output_dir),
            "--formats",
            "txt,json",
            "--model",
            "standard",
            "--language",
            "Chinese",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "sample.txt").exists()
    assert (output_dir / "sample.json").exists()
    assert "模拟转录文本" in (output_dir / "sample.txt").read_text(encoding="utf-8")
