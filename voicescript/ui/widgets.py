from __future__ import annotations

"""Reusable, animation-aware widgets that give the UI its smooth feel."""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QPushButton,
    QWidget,
)

from voicescript.ui.icons import icon_pixmap


def apply_shadow(widget: QWidget, color: str = "#c4d0e6", blur: int = 34,
                 y_offset: int = 10, alpha: int = 90) -> QGraphicsDropShadowEffect:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    shadow_color = QColor(color)
    shadow_color.setAlpha(alpha)
    effect.setColor(shadow_color)
    widget.setGraphicsEffect(effect)
    return effect


def fade_in(widget: QWidget, duration: int = 280) -> None:
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    widget._fade_anim = animation  # keep alive


class AnimatedToggle(QCheckBox):
    """iOS-style switch with an eased knob slide on toggle."""

    def __init__(self) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(52, 30)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._offset = 0.0
        self._track_on = QColor("#3f76ff")
        self._track_off = QColor("#cdd5e3")
        self._knob = QColor("#ffffff")
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def apply_colors(self, on: str, off: str, knob: str) -> None:
        self._track_on = QColor(on)
        self._track_off = QColor(off)
        self._knob = QColor(knob)
        self.update()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(52, 30)

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        super().setChecked(checked)
        self._offset = 1.0 if checked else 0.0
        self.update()

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _mix(self, a: QColor, b: QColor, t: float) -> QColor:
        return QColor(
            round(a.red() + (b.red() - a.red()) * t),
            round(a.green() + (b.green() - a.green()) * t),
            round(a.blue() + (b.blue() - a.blue()) * t),
        )

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = self._mix(self._track_off, self._track_on, self._offset)
        if not self.isEnabled():
            track = QColor("#aab3c2")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        rect = self.rect().adjusted(1, 2, -1, -2)
        radius = rect.height() / 2
        painter.drawRoundedRect(rect, radius, radius)

        knob_size = rect.height() - 6
        travel = rect.width() - knob_size - 6
        knob_x = rect.left() + 3 + travel * self._offset
        knob_y = rect.top() + 3
        painter.setBrush(self._knob)
        painter.drawEllipse(int(knob_x), knob_y, knob_size, knob_size)


class StyledComboBox(QComboBox):
    """Combo box with a crisp custom chevron that recolors with the theme."""

    def __init__(self) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chevron = "#7b879c"

    def set_chevron_color(self, color: str) -> None:
        self._chevron = color
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        pixmap = icon_pixmap("chevron-down", self._chevron, 16)
        painter = QPainter(self)
        x = self.width() - 28
        y = (self.height() - 16) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()


class IconButton(QPushButton):
    """Square, flat icon-only button used for table row actions and chrome."""

    def __init__(self, name: str, color: str, size: int = 18, box: int = 34,
                 tooltip: str = "") -> None:
        super().__init__()
        self._name = name
        self._size = size
        self.setObjectName("IconButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(box, box)
        self.set_color(color)
        if tooltip:
            self.setToolTip(tooltip)

    def set_color(self, color: str) -> None:
        from voicescript.ui.icons import make_icon

        self.setIcon(make_icon(self._name, color, self._size))
        self.setIconSize(QSize(self._size, self._size))
