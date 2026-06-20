from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voicescript import APP_NAME, APP_NAME_ZH
from voicescript.audio.probe import AudioInfo, SUPPORTED_AUDIO_EXTENSIONS, probe_audio
from voicescript.export.formats import export_txt
from voicescript.history import RecentFile, RecentFileStore
from voicescript.models import TranscriptionJobConfig, TranscriptDocument
from voicescript.runtime import ensure_std_streams
from voicescript.settings import UserPreferences, default_config_file, load_preferences, save_preferences
from voicescript.ui.icons import make_icon
from voicescript.ui.theme import ThemeName, get_theme, theme_stylesheet
from voicescript.ui.widgets import (
    AnimatedToggle,
    IconButton,
    StyledComboBox,
    apply_shadow,
    fade_in,
)
from voicescript.ui.worker import TranscriptionWorker


def install_app_fonts(app: QApplication) -> None:
    font_paths = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyhbd.ttc",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simhei.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "simsun.ttc",
    ]
    for path in font_paths:
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    for family in ("Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "SimSun", "Segoe UI"):
        app.setFont(QFont(family, 10))
        if family in QFontDatabase.families():
            break


def _format_duration(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{sec:02d}"


def _format_size(bytes_value: int) -> str:
    value = float(bytes_value)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


class UploadDropZone(QFrame):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("UploadDropZone")
        self.setProperty("dragActive", False)
        self.setAcceptDrops(True)
        self.setMinimumHeight(238)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(78, 78)
        self.icon_label.setObjectName("UploadIcon")
        self.title_label = QLabel("点击上传音频文件或拖拽到此处")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.subtitle_label = QLabel("支持 mp3、wav、m4a、aac、flac、ogg 等格式")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setObjectName("MutedLabel")
        self.choose_button = QPushButton("选择文件")
        self.choose_button.setObjectName("PrimaryButton")
        self.choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.choose_button.setFixedWidth(150)
        self.choose_button.setFixedHeight(44)

        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.choose_button, 0, Qt.AlignCenter)

    def style_icon(self, primary: str, soft: str) -> None:
        self.icon_label.setPixmap(make_icon("upload", primary, 34).pixmap(34, 34))
        self.icon_label.setStyleSheet(
            f"border-radius: 18px; background: {soft};"
        )

    def set_selected_file(self, info: AudioInfo | None) -> None:
        if info is None:
            self.title_label.setText("点击上传音频文件或拖拽到此处")
            self.subtitle_label.setText("支持 mp3、wav、m4a、aac、flac、ogg 等格式")
            return
        self.title_label.setText(info.path.name)
        self.subtitle_label.setText(
            f"时长 {_format_duration(info.duration_sec)} · 大小 {_format_size(info.size_bytes)}"
        )

    def _set_drag(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            self._set_drag(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        del event
        self._set_drag(False)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        self._set_drag(False)
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.file_dropped.emit(url.toLocalFile())
                break


class MainWindow(QMainWindow):
    NAV_ITEMS = [
        ("首页", "home"),
        ("文件列表", "list"),
        ("历史记录", "clock"),
        ("设置", "gear"),
        ("帮助与反馈", "help"),
    ]
    FEATURES = [
        ("bolt", "快速准确", "先进的 AI 语音识别技术，准确率高达 98%+"),
        ("shield", "安全可靠", "文件加密传输与存储，保护您的隐私安全"),
        ("file", "多格式支持", "支持多种音频格式，满足不同需求"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_NAME_ZH}")
        self.setWindowIcon(make_icon("waveform", "#3f76ff", 24))
        self.setMinimumSize(1200, 740)
        self.resize(1420, 820)

        self.preferences_path = default_config_file()
        self.preferences = load_preferences(self.preferences_path)
        self.theme_name = ThemeName(self.preferences.theme)
        self.history_store = RecentFileStore(self.preferences_path.with_name("recent-files.json"))
        self.selected_file: Path | None = None
        self.selected_audio: AudioInfo | None = None
        self.output_dir = self.preferences.output_dir or Path.cwd() / "transcripts"
        self.worker: TranscriptionWorker | None = None
        self.last_doc: TranscriptDocument | None = None

        self._nav_buttons: list[QPushButton] = []
        self._feature_icons: list[QLabel] = []
        self._info_dots: list[QLabel] = []
        self._cards: list[QWidget] = []
        self._combos: list[StyledComboBox] = []
        self._progress_anim: QPropertyAnimation | None = None

        self._build_ui()
        self._apply_theme()
        self._reload_history()

    # ---- layout -----------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("RootFrame")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(22)

        content_layout.addLayout(self._build_topbar())

        top_layout = QHBoxLayout()
        top_layout.setSpacing(22)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(18)
        left_layout.addWidget(self._build_upload_card(), 1)
        left_layout.addWidget(self._build_transcript_card())
        top_layout.addLayout(left_layout, 1)
        top_layout.addWidget(self._build_settings_panel())

        content_layout.addLayout(top_layout, 1)
        content_layout.addWidget(self._build_recent_card())
        root_layout.addWidget(content, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(236)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 22)
        layout.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        self.brand_icon = QLabel()
        self.brand_icon.setFixedSize(26, 26)
        brand_text = QLabel("音频转文字")
        brand_text.setStyleSheet("font-size: 16px; font-weight: 700;")
        brand_row.addWidget(self.brand_icon)
        brand_row.addWidget(brand_text)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(20)

        for index, (text, icon_name) in enumerate(self.NAV_ITEMS):
            button = QPushButton(f"  {text}")
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIconSize(QSize(20, 20))
            button.setProperty("iconName", icon_name)
            button.clicked.connect(lambda _=False, current=button: self._select_nav(current))
            self._nav_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch(1)

        self.theme_button = QPushButton("  深色模式")
        self.theme_button.setObjectName("NavButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setIconSize(QSize(20, 20))
        self.theme_button.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_button)

        self.login_button = QPushButton("  登录 / 注册")
        self.login_button.setObjectName("NavButton")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setIconSize(QSize(20, 20))
        self.login_button.setProperty("iconName", "user")
        layout.addWidget(self.login_button)
        return sidebar

    def _build_topbar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        self.avatar_button = QPushButton("  账户")
        self.avatar_button.setObjectName("AvatarButton")
        self.avatar_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_button.setFixedHeight(40)
        self.avatar_button.setIconSize(QSize(18, 18))
        row.addWidget(self.avatar_button)
        return row

    def _select_nav(self, current: QPushButton) -> None:
        for button in self._nav_buttons:
            button.setChecked(button is current)

    def _build_upload_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        self._cards.append(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 32, 36, 30)
        layout.setSpacing(16)

        title = QLabel("欢迎使用音频转文字")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        subtitle = QLabel("高效精准的语音识别，轻松将音频转换为文字")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.drop_zone = UploadDropZone()
        self.drop_zone.choose_button.clicked.connect(self._choose_file)
        self.drop_zone.file_dropped.connect(lambda value: self._set_file(Path(value)))
        layout.addWidget(self.drop_zone)

        feature_layout = QHBoxLayout()
        feature_layout.setSpacing(16)
        for icon_name, title_text, body_text in self.FEATURES:
            feature_layout.addWidget(self._feature_card(icon_name, title_text, body_text))
        layout.addLayout(feature_layout)
        return card

    def _feature_card(self, icon_name: str, title: str, body: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName("FeatureCard")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setFixedSize(44, 44)
        icon.setAlignment(Qt.AlignCenter)
        icon.setProperty("featureIcon", icon_name)
        self._feature_icons.append(icon)

        text = QLabel(f"<b>{title}</b><br><span style='color:#63708a'>{body}</span>")
        text.setTextFormat(Qt.RichText)
        text.setWordWrap(True)
        layout.addWidget(icon)
        layout.addWidget(text, 1)
        return frame

    def _build_transcript_card(self) -> QWidget:
        self.transcript_card = QFrame()
        self.transcript_card.setObjectName("PageCard")
        self.transcript_card.setVisible(False)
        self._cards.append(self.transcript_card)
        layout = QVBoxLayout(self.transcript_card)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(14)
        header = QHBoxLayout()
        title = QLabel("转录结果")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)
        copy_button = QPushButton("复制全文")
        copy_button.setObjectName("SecondaryButton")
        copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_button.clicked.connect(self._copy_transcript)
        header.addWidget(copy_button)
        open_button = QPushButton("打开文件夹")
        open_button.setObjectName("SecondaryButton")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))
        )
        header.addWidget(open_button)
        layout.addLayout(header)
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setMinimumHeight(150)
        layout.addWidget(self.transcript_text)
        return self.transcript_card

    def _build_settings_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = QFrame()
        card.setObjectName("SettingsCard")
        self._cards.append(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 26)
        card_layout.setSpacing(20)
        heading = QLabel("转录设置")
        heading.setStyleSheet("font-size: 18px; font-weight: 800;")
        card_layout.addWidget(heading)

        self.language_combo = self._combo(["中文（普通话）", "自动识别", "English", "粤语"])
        self.model_combo = self._combo(["标准模型（推荐）", "精准模型"])
        self.speaker_check = AnimatedToggle()
        self.speaker_check.setEnabled(False)
        self.punctuation_check = AnimatedToggle()
        self.punctuation_check.setChecked(True)
        self.format_combo = self._combo(["TXT 文本格式", "Markdown", "SRT 字幕", "JSON 数据", "全部格式"])

        card_layout.addLayout(self._setting_row("语言", self.language_combo))
        card_layout.addLayout(self._setting_row("转录模型", self.model_combo, "选择标准或精准识别档位"))
        card_layout.addLayout(self._setting_row("说话人识别", self.speaker_check, "区分不同发言人（暂未开放）"))
        card_layout.addLayout(self._setting_row("标点恢复", self.punctuation_check, "自动补全句读标点"))
        card_layout.addLayout(self._setting_row("输出格式", self.format_combo))

        choose_output = QPushButton(self._output_label())
        choose_output.setObjectName("SecondaryButton")
        choose_output.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_output.clicked.connect(self._choose_output_dir)
        self.output_button = choose_output
        card_layout.addWidget(choose_output)
        layout.addWidget(card)

        self.start_button = QPushButton("开始转录")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_or_cancel)
        layout.addWidget(self.start_button)
        self.status_label = QLabel("请先上传音频文件")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("MutedLabel")
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addStretch(1)
        return panel

    def _combo(self, items: list[str]) -> QComboBox:
        combo = StyledComboBox()
        combo.addItems(items)
        self._combos.append(combo)
        return combo

    def _setting_row(self, label: str, control: QWidget, hint: str = "") -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        name = QLabel(label)
        row.addWidget(name)
        if hint:
            dot = QLabel()
            dot.setFixedSize(15, 15)
            dot.setToolTip(hint)
            dot.setProperty("infoDot", True)
            self._info_dots.append(dot)
            row.addWidget(dot)
        row.addStretch(1)
        if isinstance(control, QComboBox):
            control.setMinimumWidth(170)
        row.addWidget(control)
        return row

    def _build_recent_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("RecentCard")
        self._cards.append(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)
        title_row = QHBoxLayout()
        title = QLabel("最近文件")
        title.setStyleSheet("font-size: 18px; font-weight: 800;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        all_button = QPushButton("查看全部 ›")
        all_button.setObjectName("LinkButton")
        all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        title_row.addWidget(all_button)
        layout.addLayout(title_row)

        self.recent_table = QTableWidget(0, 6)
        self.recent_table.setHorizontalHeaderLabels(
            ["文件名", "时长", "大小", "转录时间", "状态", "操作"]
        )
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setShowGrid(False)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.recent_table.verticalHeader().setDefaultSectionSize(52)
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            self.recent_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.recent_table.setMinimumHeight(150)
        self.recent_table.cellDoubleClicked.connect(self._open_history_output)
        layout.addWidget(self.recent_table)
        return card

    # ---- theming ----------------------------------------------------------
    def _apply_theme(self) -> None:
        token = get_theme(self.theme_name)
        self.setStyleSheet(theme_stylesheet(self.theme_name) + self._dynamic_styles(token))
        is_dark = self.theme_name is ThemeName.DARK

        self.brand_icon.setPixmap(make_icon("waveform", token.primary, 26).pixmap(26, 26))
        for button in self._nav_buttons:
            name = button.property("iconName")
            color = token.primary if button.isChecked() else token.icon
            button.setIcon(make_icon(name, color, 20))
        self.theme_button.setText("  浅色模式" if is_dark else "  深色模式")
        self.theme_button.setIcon(make_icon("sun" if is_dark else "moon", token.icon, 20))
        self.login_button.setIcon(make_icon("user", token.icon, 20))
        self.avatar_button.setIcon(make_icon("user", token.primary, 18))

        self.drop_zone.style_icon(token.primary, token.primary_soft)
        for icon in self._feature_icons:
            name = icon.property("featureIcon")
            icon.setPixmap(make_icon(name, token.primary, 22).pixmap(22, 22))
            icon.setStyleSheet(f"background: {token.primary_soft}; border-radius: 12px;")
        for dot in self._info_dots:
            dot.setPixmap(make_icon("info", token.icon, 15).pixmap(15, 15))
        for combo in self._combos:
            combo.set_chevron_color(token.icon)

        self.speaker_check.apply_colors(token.primary, token.track, "#ffffff")
        self.punctuation_check.apply_colors(token.primary, token.track, "#ffffff")

        shadow = token.shadow
        alpha = 120 if not is_dark else 160
        for card in self._cards:
            apply_shadow(card, shadow, blur=36, y_offset=12, alpha=alpha)
        self._restyle_history_actions(token)

    def _dynamic_styles(self, token) -> str:
        return f"""
        #MutedLabel {{ color: {token.muted_text}; }}
        QLabel[infoDot="true"] {{ }}
        """

    def _toggle_theme(self) -> None:
        self.theme_name = ThemeName.DARK if self.theme_name is ThemeName.LIGHT else ThemeName.LIGHT
        self.preferences = UserPreferences(theme=self.theme_name.value, output_dir=self.output_dir)
        save_preferences(self.preferences, self.preferences_path)
        self._apply_theme()

    # ---- actions ----------------------------------------------------------
    def _output_label(self) -> str:
        text = str(self.output_dir)
        if len(text) > 30:
            text = "…" + text[-29:]
        return f"保存位置：{text}"

    def _choose_file(self) -> None:
        filters = "Audio Files (" + " ".join(f"*{ext}" for ext in sorted(SUPPORTED_AUDIO_EXTENSIONS)) + ")"
        path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", str(Path.home()), filters)
        if path:
            self._set_file(Path(path))

    def _set_file(self, path: Path) -> None:
        try:
            info = probe_audio(path)
        except Exception as exc:
            QMessageBox.warning(self, "无法读取音频", str(exc))
            self.status_label.setText("音频文件不可读")
            self.start_button.setEnabled(False)
            return
        self.selected_file = path
        self.selected_audio = info
        self.drop_zone.set_selected_file(info)
        self.status_label.setText(f"已选择：{path.name}")
        self.start_button.setEnabled(True)

    def _choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择保存位置", str(self.output_dir))
        if path:
            self.output_dir = Path(path)
            self.output_button.setText(self._output_label())
            save_preferences(
                UserPreferences(theme=self.theme_name.value, output_dir=self.output_dir),
                self.preferences_path,
            )

    def _selected_formats(self) -> tuple[str, ...]:
        mapping = {
            "TXT 文本格式": ("txt",),
            "Markdown": ("md",),
            "SRT 字幕": ("srt",),
            "JSON 数据": ("json",),
            "全部格式": ("all",),
        }
        return mapping[self.format_combo.currentText()]

    def _selected_language(self) -> str | None:
        value = self.language_combo.currentText()
        return None if value == "自动识别" else value

    def _selected_profile(self) -> str:
        return "precise" if self.model_combo.currentText() == "精准模型" else "standard"

    def _start_or_cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("正在取消...")
            self.start_button.setEnabled(False)
            return
        if not self.selected_file:
            return
        config = TranscriptionJobConfig(
            input_file=self.selected_file,
            language=self._selected_language(),
            model_profile=self._selected_profile(),
            output_dir=self.output_dir,
            output_formats=self._selected_formats(),
            restore_punctuation=self.punctuation_check.isChecked(),
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.start_button.setText("取消转录")
        self.status_label.setText("准备转录...")
        self.worker = TranscriptionWorker(config, use_mock=os.environ.get("VOICESCRIPT_USE_MOCK_ASR") == "1")
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _animate_progress(self, target: int) -> None:
        if self._progress_anim is not None:
            self._progress_anim.stop()
        animation = QPropertyAnimation(self.progress_bar, b"value", self)
        animation.setDuration(280)
        animation.setStartValue(self.progress_bar.value())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()
        self._progress_anim = animation

    def _on_progress(self, value: float, message: str) -> None:
        self._animate_progress(max(0, min(100, int(value * 100))))
        self.status_label.setText(message)

    def _on_completed(self, doc: TranscriptDocument, paths: list[Path]) -> None:
        self.last_doc = doc
        self.start_button.setText("重新转录")
        self.start_button.setEnabled(True)
        self._animate_progress(100)
        self.status_label.setText("转录完成")
        was_hidden = not self.transcript_card.isVisible()
        self.transcript_card.setVisible(True)
        self.transcript_text.setPlainText(export_txt(doc, self.punctuation_check.isChecked()))
        if was_hidden:
            fade_in(self.transcript_card)
        self._add_history(doc, "已完成")
        self._reload_history()
        if paths:
            self.status_label.setText(f"转录完成：{paths[0].parent}")

    def _on_failed(self, message: str) -> None:
        self.start_button.setText("开始转录")
        self.start_button.setEnabled(bool(self.selected_file))
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"转录失败：{message}")
        QMessageBox.warning(self, "转录失败", message)
        if self.selected_audio and self.selected_file:
            self._add_history_failed(self.selected_file, self.selected_audio)
            self._reload_history()

    # ---- history ----------------------------------------------------------
    def _add_history(self, doc: TranscriptDocument, status: str) -> None:
        item = RecentFile(
            file_path=doc.source_file,
            duration_label=_format_duration(doc.duration_sec),
            size_label=_format_size(doc.source_file.stat().st_size) if doc.source_file.exists() else "",
            transcribed_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            status=status,
            output_dir=self.output_dir,
        )
        self.history_store.add(item)

    def _add_history_failed(self, path: Path, info: AudioInfo) -> None:
        self.history_store.add(
            RecentFile(
                file_path=path,
                duration_label=_format_duration(info.duration_sec),
                size_label=_format_size(info.size_bytes),
                transcribed_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                status="失败",
                output_dir=self.output_dir,
            )
        )

    def _reload_history(self) -> None:
        items = self.history_store.load()
        token = get_theme(self.theme_name)
        self.recent_table.setRowCount(len(items))
        for row, item in enumerate(items):
            name_item = QTableWidgetItem("  " + item.file_path.name)
            name_item.setIcon(make_icon("music", token.primary, 18))
            self.recent_table.setItem(row, 0, name_item)
            for column, value in enumerate(
                [item.duration_label, item.size_label, item.transcribed_at], start=1
            ):
                self.recent_table.setItem(row, column, QTableWidgetItem(value))
            self.recent_table.setCellWidget(row, 4, self._status_badge(item.status, token))
            self.recent_table.setCellWidget(row, 5, self._row_actions(item, token))

    def _status_badge(self, status: str, token) -> QWidget:
        ok = status == "已完成"
        wrap = QWidget()
        box = QHBoxLayout(wrap)
        box.setContentsMargins(8, 0, 8, 0)
        label = QLabel(status)
        label.setAlignment(Qt.AlignCenter)
        bg = token.success_bg if ok else "#fde8e8"
        fg = token.success_text if ok else "#c0392b"
        label.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 10px;"
            f" padding: 4px 12px; font-size: 12px; font-weight: 600;"
        )
        box.addWidget(label, 0, Qt.AlignCenter)
        return wrap

    def _row_actions(self, item: RecentFile, token) -> QWidget:
        wrap = QWidget()
        box = QHBoxLayout(wrap)
        box.setContentsMargins(4, 0, 4, 0)
        box.setSpacing(2)
        open_dir = IconButton("folder", token.icon, 18, 32, tooltip="打开所在文件夹")
        open_dir.clicked.connect(
            lambda _=False, path=str(item.output_dir): QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        )
        file_btn = IconButton("file", token.icon, 18, 32, tooltip="查看转录文件")
        file_btn.clicked.connect(
            lambda _=False, path=str(item.output_dir): QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        )
        more_btn = IconButton("more", token.icon, 18, 32, tooltip="更多")
        box.addStretch(1)
        for button in (file_btn, open_dir, more_btn):
            box.addWidget(button)
        return wrap

    def _restyle_history_actions(self, token) -> None:
        # Re-render row widgets so icons/badges follow the active theme.
        if hasattr(self, "recent_table"):
            self._reload_history()

    def _open_history_output(self, row: int, _column: int) -> None:
        items = self.history_store.load()
        if 0 <= row < len(items):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(items[row].output_dir)))

    def _copy_transcript(self) -> None:
        QApplication.clipboard().setText(self.transcript_text.toPlainText())
        self.status_label.setText("已复制全文")


def main() -> int:
    ensure_std_streams()
    if "--self-test" in sys.argv:
        try:
            from voicescript.asr.qwen import prepare_qwen_runtime

            prepare_qwen_runtime()
            from qwen_asr import Qwen3ASRModel  # noqa: F401
            return 0
        except Exception:
            Path("voicescript-self-test.log").write_text(traceback.format_exc(), encoding="utf-8")
            return 1
    app = QApplication.instance() or QApplication([])
    install_app_fonts(app)
    window = MainWindow()
    window.setWindowOpacity(0.0)
    window.show()
    window_fade = QPropertyAnimation(window, b"windowOpacity", window)
    window_fade.setDuration(260)
    window_fade.setStartValue(0.0)
    window_fade.setEndValue(1.0)
    window_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    window_fade.start()
    window._intro_anim = window_fade  # keep alive
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
