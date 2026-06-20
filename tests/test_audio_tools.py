from pathlib import Path

from voicescript.audio.probe import (
    SUPPORTED_AUDIO_EXTENSIONS,
    build_ffmpeg_command,
    is_supported_audio_file,
)


def test_supported_audio_extensions_cover_apple_and_android_formats():
    expected = {
        ".m4a",
        ".aac",
        ".caf",
        ".amr",
        ".3gp",
        ".ogg",
        ".opus",
        ".mp3",
        ".wav",
        ".flac",
    }

    assert expected.issubset(SUPPORTED_AUDIO_EXTENSIONS)
    assert is_supported_audio_file(Path("F:/声笺录/录音 001.m4a"))
    assert is_supported_audio_file(Path("F:/声笺录/android-call.amr"))
    assert not is_supported_audio_file(Path("notes.docx"))


def test_ffmpeg_command_handles_unicode_paths_and_normalizes_to_16k_mono_wav():
    command = build_ffmpeg_command(
        input_file=Path("F:/声笺录/会议 记录.m4a"),
        output_file=Path("F:/声笺录/cache/会议 记录.wav"),
    )

    assert command[:2] == ["ffmpeg", "-y"]
    assert str(Path("F:/声笺录/会议 记录.m4a")) in command
    assert str(Path("F:/声笺录/cache/会议 记录.wav")) in command
    assert "-ar" in command
    assert "16000" in command
    assert "-ac" in command
    assert "1" in command
