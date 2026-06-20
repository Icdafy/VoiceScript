from pathlib import Path

from voicescript.settings import UserPreferences, load_preferences, save_preferences


def test_preferences_persist_theme_and_output_directory(tmp_path):
    config_file = tmp_path / "preferences.json"
    expected = UserPreferences(theme="dark", output_dir=Path("F:/声笺录/transcripts"))

    save_preferences(expected, config_file)
    actual = load_preferences(config_file)

    assert actual.theme == "dark"
    assert actual.output_dir == Path("F:/声笺录/transcripts")
