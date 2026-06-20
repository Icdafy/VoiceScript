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
    border_soft: str
    input_border: str
    primary: str
    primary_hover: str
    primary_soft: str
    nav_hover: str
    track: str
    icon: str
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
        border_soft="#eef2fa",
        input_border="#dfe6f2",
        primary="#3f76ff",
        primary_hover="#2f63ee",
        primary_soft="#edf3ff",
        nav_hover="#f2f6ff",
        track="#cdd5e3",
        icon="#7b879c",
        success_bg="#dcfce7",
        success_text="#16803a",
        shadow="#d9e2f2",
    ),
    ThemeName.DARK: ThemeTokens(
        background="#0d1117",
        surface="#161b22",
        surface_muted="#1b212b",
        text="#f6f8fa",
        muted_text="#a6b0c3",
        border="#161b22",
        border_soft="#161b22",
        input_border="#2b333f",
        primary="#78a0ff",
        primary_hover="#8fb0ff",
        primary_soft="#1d2a44",
        nav_hover="#1b212b",
        track="#3a4453",
        icon="#9aa6ba",
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
    t = get_theme(theme)
    return f"""
    QMainWindow {{
        background: {t.background};
    }}
    QWidget {{
        color: {t.text};
        font-family: "Microsoft YaHei UI", "Segoe UI";
        font-size: 14px;
    }}
    #RootFrame {{
        background: {t.background};
    }}
    #ContentScroll {{
        background: transparent;
        border: none;
    }}
    #ContentScroll > QWidget {{
        background: {t.background};
    }}
    #Sidebar {{
        background: {t.surface};
        border-right: 1px solid {t.border_soft};
    }}
    #PageCard, #SettingsCard, #RecentCard {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: 20px;
    }}
    #UploadDropZone {{
        background: {t.surface_muted};
        border: 2px dashed {t.input_border};
        border-radius: 16px;
    }}
    #UploadDropZone[dragActive="true"] {{
        background: {t.primary_soft};
        border: 2px dashed {t.primary};
    }}
    #FeatureCard {{
        background: {t.surface_muted};
        border: 1px solid transparent;
        border-radius: 14px;
    }}
    #FeatureCard:hover {{
        border: 1px solid {t.input_border};
    }}
    #PrimaryButton {{
        background: {t.primary};
        color: #ffffff;
        border: none;
        border-radius: 12px;
        min-height: 48px;
        padding: 0 28px;
        font-size: 15px;
        font-weight: 600;
    }}
    #PrimaryButton:hover {{
        background: {t.primary_hover};
    }}
    #PrimaryButton:disabled {{
        background: {t.primary_soft};
        color: {t.muted_text};
    }}
    #SecondaryButton {{
        background: {t.surface_muted};
        color: {t.text};
        border: 1px solid {t.input_border};
        border-radius: 10px;
        min-height: 40px;
        padding: 0 18px;
    }}
    #SecondaryButton:hover {{
        background: {t.nav_hover};
        border: 1px solid {t.primary};
        color: {t.primary};
    }}
    #LinkButton {{
        background: transparent;
        border: none;
        color: {t.muted_text};
        padding: 4px 8px;
    }}
    #LinkButton:hover {{
        color: {t.primary};
    }}
    #IconButton {{
        background: transparent;
        border: none;
        border-radius: 9px;
    }}
    #IconButton:hover {{
        background: {t.nav_hover};
    }}
    QPushButton#NavButton {{
        background: transparent;
        border: none;
        border-radius: 12px;
        min-height: 46px;
        padding-left: 14px;
        text-align: left;
        color: {t.muted_text};
        font-size: 14px;
    }}
    QPushButton#NavButton:hover {{
        background: {t.nav_hover};
    }}
    QPushButton#NavButton:checked {{
        background: {t.primary_soft};
        color: {t.primary};
        font-weight: 600;
    }}
    QComboBox {{
        min-height: 44px;
        padding: 0 38px 0 14px;
        border: 1px solid {t.input_border};
        border-radius: 10px;
        background: {t.surface};
        selection-background-color: {t.primary_soft};
    }}
    QComboBox:hover {{
        border: 1px solid {t.primary};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 36px;
    }}
    QComboBox::down-arrow {{
        image: none;
        width: 0;
        height: 0;
    }}
    QComboBox QAbstractItemView {{
        border: 1px solid {t.input_border};
        border-radius: 12px;
        background: {t.surface};
        padding: 6px;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 34px;
        border-radius: 8px;
        padding: 0 10px;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {t.primary_soft};
        color: {t.primary};
    }}
    QTableWidget {{
        background: transparent;
        border: none;
        outline: none;
        selection-background-color: {t.primary_soft};
        selection-color: {t.text};
    }}
    QTableWidget::item {{
        padding: 6px 4px;
        border-bottom: 1px solid {t.border_soft};
    }}
    QTableWidget::item:selected {{
        background: {t.nav_hover};
        color: {t.text};
    }}
    QHeaderView {{
        background: transparent;
        border: none;
    }}
    QHeaderView::section {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {t.input_border};
        color: {t.muted_text};
        padding: 10px 4px;
        font-size: 13px;
    }}
    QTableCornerButton::section {{
        background: transparent;
        border: none;
    }}
    QProgressBar {{
        min-height: 20px;
        border: none;
        border-radius: 10px;
        background: {t.surface_muted};
        text-align: center;
        color: {t.muted_text};
        font-size: 12px;
    }}
    QProgressBar::chunk {{
        border-radius: 10px;
        background: {t.primary};
    }}
    QTextEdit {{
        background: {t.surface_muted};
        border: 1px solid {t.input_border};
        border-radius: 14px;
        padding: 14px;
        selection-background-color: {t.primary_soft};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.track};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t.muted_text};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QToolTip {{
        background: {t.text};
        color: {t.surface};
        border: none;
        border-radius: 6px;
        padding: 6px 10px;
    }}
    """
