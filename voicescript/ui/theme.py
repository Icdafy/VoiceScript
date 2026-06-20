from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThemeName(str, Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class ThemeTokens:
    background: str
    surface: str
    surface_muted: str
    text: str
    muted_text: str
    border: str
    primary: str
    primary_soft: str
    success_bg: str
    success_text: str
    shadow: str


THEMES = {
    ThemeName.LIGHT: ThemeTokens(
        background="#f7faff",
        surface="#ffffff",
        surface_muted="#f5f8ff",
        text="#121826",
        muted_text="#63708a",
        border="#e6ecf7",
        primary="#3f76ff",
        primary_soft="#edf3ff",
        success_bg="#dcfce7",
        success_text="#16803a",
        shadow="#d9e2f2",
    ),
    ThemeName.DARK: ThemeTokens(
        background="#0d1117",
        surface="#161b22",
        surface_muted="#1f2630",
        text="#f6f8fa",
        muted_text="#a6b0c3",
        border="#303846",
        primary="#78a0ff",
        primary_soft="#1d2a44",
        success_bg="#113322",
        success_text="#6ee7a8",
        shadow="#05070a",
    ),
}


def get_theme(theme: ThemeName | str) -> ThemeTokens:
    if isinstance(theme, ThemeName):
        return THEMES[theme]
    return THEMES[ThemeName(str(theme))]


def theme_stylesheet(theme: ThemeName | str) -> str:
    token = get_theme(theme)
    return f"""
    QMainWindow {{
        background: {token.background};
        color: {token.text};
        font-family: "Microsoft YaHei UI", "Segoe UI";
        font-size: 14px;
    }}
    QWidget {{
        color: {token.text};
        font-family: "Microsoft YaHei UI", "Segoe UI";
    }}
    #RootFrame {{
        background: {token.background};
    }}
    #Sidebar {{
        background: {token.surface};
        border-right: 1px solid {token.border};
    }}
    #PageCard, #SettingsCard, #RecentCard {{
        background: {token.surface};
        border: 1px solid {token.border};
        border-radius: 18px;
    }}
    #UploadDropZone {{
        background: {token.surface};
        border: 2px dashed #b8ccff;
        border-radius: 16px;
    }}
    #PrimaryButton {{
        background: {token.primary};
        color: white;
        border: none;
        border-radius: 9px;
        min-height: 44px;
        padding: 0 28px;
        font-weight: 600;
    }}
    #PrimaryButton:disabled {{
        background: #bcd0ff;
        color: rgba(255, 255, 255, 0.75);
    }}
    #SecondaryButton {{
        background: {token.primary_soft};
        color: {token.primary};
        border: 1px solid {token.border};
        border-radius: 9px;
        min-height: 38px;
        padding: 0 18px;
    }}
    QPushButton#NavButton {{
        background: transparent;
        border: none;
        border-radius: 10px;
        min-height: 48px;
        padding-left: 18px;
        text-align: left;
        color: {token.muted_text};
    }}
    QPushButton#NavButton:checked {{
        background: {token.primary_soft};
        color: {token.primary};
        font-weight: 600;
    }}
    QComboBox {{
        min-height: 42px;
        padding: 0 34px 0 14px;
        border: 1px solid {token.border};
        border-radius: 8px;
        background: {token.surface};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 34px;
    }}
    QComboBox::down-arrow {{
        image: none;
        width: 0;
        height: 0;
    }}
    QCheckBox::indicator {{
        width: 42px;
        height: 24px;
    }}
    QTableWidget {{
        background: transparent;
        border: none;
        gridline-color: {token.border};
        selection-background-color: {token.primary_soft};
    }}
    QHeaderView::section {{
        background: transparent;
        border: none;
        color: {token.muted_text};
        padding: 8px;
    }}
    QProgressBar {{
        height: 10px;
        border: none;
        border-radius: 5px;
        background: {token.surface_muted};
    }}
    QProgressBar::chunk {{
        border-radius: 5px;
        background: {token.primary};
    }}
    QTextEdit {{
        background: {token.surface_muted};
        border: 1px solid {token.border};
        border-radius: 12px;
        padding: 12px;
    }}
    """
