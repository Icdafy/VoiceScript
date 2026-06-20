from types import SimpleNamespace

from voicescript.asr.qwen import MODEL_PROFILES, QwenModelProfile, _segments_from_timestamps


def test_qwen_model_profiles_map_to_official_checkpoints():
    standard = MODEL_PROFILES[QwenModelProfile.STANDARD]
    precise = MODEL_PROFILES[QwenModelProfile.PRECISE]

    assert standard.asr_checkpoint == "Qwen/Qwen3-ASR-0.6B"
    assert precise.asr_checkpoint == "Qwen/Qwen3-ASR-1.7B"
    assert standard.aligner_checkpoint == "Qwen/Qwen3-ForcedAligner-0.6B"
    assert precise.aligner_checkpoint == "Qwen/Qwen3-ForcedAligner-0.6B"


def test_standard_profile_is_default_for_six_gb_windows_machine():
    assert QwenModelProfile.default() is QwenModelProfile.STANDARD


def test_zero_length_alignment_falls_back_to_audio_duration():
    segments = _segments_from_timestamps(
        [SimpleNamespace(text="嗯", start_time=0.0, end_time=0.0)],
        fallback_text="嗯",
        duration_sec=1.0,
    )

    assert segments[0].start_sec == 0.0
    assert segments[0].end_sec == 1.0
