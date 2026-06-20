from __future__ import annotations

from enum import Enum


class ThemeMode(str, Enum):
    BLACK = "black"
    WHITE = "white"


def build_stylesheet(mode: ThemeMode) -> str:
    if mode == ThemeMode.WHITE:
        tokens = {
            "window": "#f5f5f2",
            "surface": "#ffffff",
            "surface_alt": "#ecebe6",
            "chrome": "rgba(255, 255, 255, 190)",
            "text": "#171717",
            "muted": "#64645f",
            "border": "#d3d1c9",
            "accent": "#166534",
            "accent_text": "#ffffff",
            "warning": "#a16207",
            "selection": "#dcfce7",
        }
    else:
        tokens = {
            "window": "#0f100d",
            "surface": "#181915",
            "surface_alt": "#23251f",
            "chrome": "rgba(36, 38, 32, 210)",
            "text": "#f5f5ef",
            "muted": "#a8a89f",
            "border": "#3a3d33",
            "accent": "#84cc16",
            "accent_text": "#10120d",
            "warning": "#fbbf24",
            "selection": "#26351d",
        }

    return f"""
QMainWindow {{
    background: {tokens["window"]};
    color: {tokens["text"]};
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 14px;
}}
QWidget {{
    color: {tokens["text"]};
}}
QFrame#ChromePanel, QFrame#DropZone {{
    background: {tokens["chrome"]};
    border: 1px solid {tokens["border"]};
    border-radius: 8px;
}}
QFrame#ContentSurface, QTableWidget, QTextEdit {{
    background: {tokens["surface"]};
    border: 1px solid {tokens["border"]};
    border-radius: 6px;
}}
QLabel#Brand {{
    font-size: 24px;
    font-weight: 700;
}}
QLabel#Motto, QLabel#Muted {{
    color: {tokens["muted"]};
}}
QPushButton, QComboBox {{
    min-height: 44px;
    padding: 0 14px;
    border-radius: 8px;
    border: 1px solid {tokens["border"]};
    background: {tokens["surface_alt"]};
}}
QPushButton:hover, QComboBox:hover {{
    border-color: {tokens["accent"]};
}}
QPushButton:pressed {{
    padding-top: 2px;
}}
QPushButton#PrimaryButton {{
    background: {tokens["accent"]};
    color: {tokens["accent_text"]};
    font-weight: 700;
}}
QPushButton:disabled {{
    color: {tokens["muted"]};
    background: {tokens["surface_alt"]};
}}
QProgressBar {{
    min-height: 12px;
    border-radius: 6px;
    background: {tokens["surface_alt"]};
    border: 1px solid {tokens["border"]};
    text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 5px;
    background: {tokens["accent"]};
}}
QTableWidget {{
    gridline-color: {tokens["border"]};
    alternate-background-color: {tokens["surface_alt"]};
    selection-background-color: {tokens["selection"]};
}}
QHeaderView::section {{
    background: {tokens["surface_alt"]};
    color: {tokens["muted"]};
    border: 0;
    border-bottom: 1px solid {tokens["border"]};
    padding: 8px;
}}
QStatusBar {{
    background: {tokens["window"]};
    color: {tokens["muted"]};
}}
QToolTip {{
    background: {tokens["surface"]};
    color: {tokens["text"]};
    border: 1px solid {tokens["border"]};
    padding: 6px;
}}
"""
