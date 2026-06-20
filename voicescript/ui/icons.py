from __future__ import annotations

"""Crisp, theme-aware line icons rendered from inline SVG.

The whole UI uses a single visual language: 24x24 stroke icons with round
caps/joins. Colors are injected at render time so the same glyph works on
light and dark themes and as active/inactive navigation states.
"""

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Each entry is the inner body of a 0 0 24 24 SVG. `{c}` is replaced with the
# stroke color. Filled accents use `{c}` for fill as well.
_PATHS: dict[str, str] = {
    "waveform": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round">'
        '<line x1="4" y1="10" x2="4" y2="14"/>'
        '<line x1="8" y1="6" x2="8" y2="18"/>'
        '<line x1="12" y1="3" x2="12" y2="21"/>'
        '<line x1="16" y1="6" x2="16" y2="18"/>'
        '<line x1="20" y1="10" x2="20" y2="14"/></g>'
    ),
    "home": (
        '<path d="M4 11.5 12 4l8 7.5" fill="none" stroke="{c}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M6 10.5V20h12v-9.5" fill="none" stroke="{c}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M10 20v-5h4v5" fill="none" stroke="{c}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "list": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" fill="none">'
        '<rect x="4" y="4" width="16" height="16" rx="3"/>'
        '<line x1="8" y1="9" x2="16" y2="9"/>'
        '<line x1="8" y1="13" x2="16" y2="13"/>'
        '<line x1="8" y1="17" x2="13" y2="17"/></g>'
    ),
    "clock": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<circle cx="12" cy="12" r="8.2"/>'
        '<path d="M12 7.6V12l3 1.8"/></g>'
    ),
    "gear": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 3v2.2M12 18.8V21M21 12h-2.2M5.2 12H3M18.4 5.6l-1.6 1.6'
        'M7.2 16.8l-1.6 1.6M18.4 18.4l-1.6-1.6M7.2 7.2 5.6 5.6"/></g>'
    ),
    "help": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<circle cx="12" cy="12" r="8.2"/>'
        '<path d="M9.6 9.4a2.5 2.5 0 1 1 3.2 2.6c-.7.3-.8.8-.8 1.5"/>'
        '<circle cx="12" cy="16.5" r="0.6" fill="{c}" stroke="none"/></g>'
    ),
    "user": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<circle cx="12" cy="8.5" r="3.6"/>'
        '<path d="M5.5 19.5a6.5 6.5 0 0 1 13 0"/></g>'
    ),
    "upload": (
        '<g stroke="{c}" stroke-width="2.2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<path d="M12 16V5"/>'
        '<path d="M7.5 9.5 12 5l4.5 4.5"/>'
        '<path d="M5 19h14"/></g>'
    ),
    "bolt": (
        '<path d="M13 2 5 13.5h5L9 22l9-12h-5z" fill="{c}" stroke="{c}" '
        'stroke-width="1.4" stroke-linejoin="round"/>'
    ),
    "shield": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<path d="M12 3 5 6v5.5c0 4 3 7.4 7 9 4-1.6 7-5 7-9V6z"/>'
        '<path d="m9 12 2 2 4-4.2"/></g>'
    ),
    "file": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<path d="M7 3h6l5 5v13H7z"/>'
        '<path d="M13 3v5h5"/>'
        '<path d="M9.5 13h5M9.5 16.5h5"/></g>'
    ),
    "music": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<path d="M9 18V6l9-2v12"/>'
        '<circle cx="6.5" cy="18" r="2.5"/>'
        '<circle cx="15.5" cy="16" r="2.5"/></g>'
    ),
    "folder": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<path d="M4 7.5C4 6.7 4.7 6 5.5 6h3.2l2 2.2h7.8c.8 0 1.5.7 1.5 1.5'
        'v7.8c0 .8-.7 1.5-1.5 1.5h-13C4.7 19 4 18.3 4 17.5z"/></g>'
    ),
    "more": (
        '<g fill="{c}">'
        '<circle cx="5.5" cy="12" r="1.7"/>'
        '<circle cx="12" cy="12" r="1.7"/>'
        '<circle cx="18.5" cy="12" r="1.7"/></g>'
    ),
    "info": (
        '<g stroke="{c}" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<circle cx="12" cy="12" r="8.2"/>'
        '<path d="M12 11v5"/>'
        '<circle cx="12" cy="8" r="0.7" fill="{c}" stroke="none"/></g>'
    ),
    "chevron-down": (
        '<path d="M6 9.5 12 15l6-5.5" fill="none" stroke="{c}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "copy": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" fill="none">'
        '<rect x="8" y="8" width="12" height="12" rx="2.5"/>'
        '<path d="M5 16H4.5A1.5 1.5 0 0 1 3 14.5v-10A1.5 1.5 0 0 1 4.5 3h10'
        'A1.5 1.5 0 0 1 16 4.5V5"/></g>'
    ),
    "sun": (
        '<g stroke="{c}" stroke-width="2" stroke-linecap="round" fill="none">'
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2.5V5M12 19v2.5M21.5 12H19M5 12H2.5M18.4 5.6 16.7 7.3'
        'M7.3 16.7 5.6 18.4M18.4 18.4 16.7 16.7M7.3 7.3 5.6 5.6"/></g>'
    ),
    "moon": (
        '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" fill="none" '
        'stroke="{c}" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"/>'
    ),
    "check": (
        '<path d="m5 12.5 4.2 4.2L19 7" fill="none" stroke="{c}" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "close": (
        '<path d="M6 6l12 12M18 6 6 18" fill="none" stroke="{c}" '
        'stroke-width="2" stroke-linecap="round"/>'
    ),
}


def icon_svg(name: str, color: str) -> str:
    body = _PATHS[name].format(c=color)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'width="24" height="24">{body}</svg>'
    )


@lru_cache(maxsize=256)
def icon_pixmap(name: str, color: str, size: int = 22, ratio: int = 2) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(icon_svg(name, color).encode("utf-8")))
    pixmap = QPixmap(size * ratio, size * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return pixmap


def make_icon(name: str, color: str, size: int = 22) -> QIcon:
    return QIcon(icon_pixmap(name, color, size))
