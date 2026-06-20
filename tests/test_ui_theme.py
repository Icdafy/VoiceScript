from voicescript.ui.theme import ThemeName, get_theme, theme_stylesheet


def test_light_and_dark_themes_define_reference_surface_tokens():
    light = get_theme(ThemeName.LIGHT)
    dark = get_theme(ThemeName.DARK)

    assert light.background == "#f7faff"
    assert light.primary == "#3f76ff"
    assert dark.background == "#0d1117"
    assert dark.primary == "#78a0ff"


def test_theme_stylesheet_contains_core_widget_selectors():
    stylesheet = theme_stylesheet(ThemeName.LIGHT)

    assert "QMainWindow" in stylesheet
    assert "#Sidebar" in stylesheet
    assert "#UploadDropZone" in stylesheet
    assert "#PrimaryButton" in stylesheet
