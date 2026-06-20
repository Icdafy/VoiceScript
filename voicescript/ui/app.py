from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QStyle,
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
from voicescript.ui.theme import ThemeName, theme_stylesheet
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
        self.setAcceptDrops(True)
        self.setMinimumHeight(230)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        self.icon_label = QLabel("↑")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(84, 84)
        self.icon_label.setStyleSheet(
            "border-radius: 20px; background: #edf3ff; color: #3f76ff; font-size: 42px; font-weight: 700;"
        )
        self.title_label = QLabel("点击上传音频文件或拖拽到此处")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.subtitle_label = QLabel("支持 mp3、wav、m4a、aac、flac、ogg 等格式")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #63708a;")
        self.choose_button = QPushButton("选择文件")
        self.choose_button.setObjectName("PrimaryButton")
        self.choose_button.setFixedWidth(150)

        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.choose_button, 0, Qt.AlignCenter)

    def set_selected_file(self, info: AudioInfo | None) -> None:
        if info is None:
            self.title_label.setText("点击上传音频文件或拖拽到此处")
            self.subtitle_label.setText("支持 mp3、wav、m4a、aac、flac、ogg 等格式")
            return
        self.title_label.setText(info.path.name)
        self.subtitle_label.setText(f"时长 {_format_duration(info.duration_sec)} · 大小 {_format_size(info.size_bytes)}")

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.file_dropped.emit(url.toLocalFile())
                break


class ToggleSwitch(QCheckBox):
    def __init__(self) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(52, 28)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(52, 28)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track = QColor("#3f76ff" if self.isChecked() else "#b7bfcd")
        if not self.isEnabled():
            track = QColor("#aab3c2")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        track_rect = self.rect().adjusted(1, 2, -1, -2)
        painter.drawRoundedRect(track_rect, 12, 12)

        knob_size = 22
        knob_y = track_rect.center().y() - knob_size // 2
        knob_x = track_rect.right() - knob_size - 2 if self.isChecked() else track_rect.left() + 2
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(knob_x, knob_y, knob_size, knob_size)


class StyledComboBox(QComboBox):
    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#63708a"), 1.6))
        center_x = self.width() - 22
        center_y = self.height() // 2 + 1
        painter.drawLine(center_x - 5, center_y - 3, center_x, center_y + 2)
        painter.drawLine(center_x, center_y + 2, center_x + 5, center_y - 3)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_NAME_ZH}")
        self.setMinimumSize(1280, 760)
        self.resize(1420, 800)

        self.preferences_path = default_config_file()
        self.preferences = load_preferences(self.preferences_path)
        self.theme_name = ThemeName(self.preferences.theme)
        self.history_store = RecentFileStore(self.preferences_path.with_name("recent-files.json"))
        self.selected_file: Path | None = None
        self.selected_audio: AudioInfo | None = None
        self.output_dir = self.preferences.output_dir or Path.cwd() / "transcripts"
        self.worker: TranscriptionWorker | None = None
        self.last_doc: TranscriptDocument | None = None

        self._build_ui()
        self._apply_theme()
        self._reload_history()

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
        content_layout.setContentsMargins(24, 28, 28, 24)
        content_layout.setSpacing(24)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(24)
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
        sidebar.setFixedWidth(240)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 24)
        layout.setSpacing(14)

        brand = QLabel("<b>音频转文字</b>")
        brand.setTextFormat(Qt.RichText)
        brand.setStyleSheet("font-size: 15px;")
        layout.addWidget(brand)
        layout.addSpacing(22)

        nav_items = [
            ("首页", QStyle.StandardPixmap.SP_DirHomeIcon),
            ("文件列表", QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ("历史记录", QStyle.StandardPixmap.SP_BrowserReload),
            ("设置", QStyle.StandardPixmap.SP_FileDialogContentsView),
            ("帮助与反馈", QStyle.StandardPixmap.SP_MessageBoxQuestion),
        ]
        group: list[QPushButton] = []
        for index, (text, icon) in enumerate(nav_items):
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setIcon(self.style().standardIcon(icon))
            button.clicked.connect(lambda _=False, current=button: self._select_nav(current, group))
            group.append(button)
            layout.addWidget(button)
        layout.addStretch(1)

        self.theme_button = QPushButton("切换深色")
        self.theme_button.setObjectName("SecondaryButton")
        self.theme_button.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_button)
        login = QPushButton("登录 / 注册")
        login.setObjectName("NavButton")
        login.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        layout.addWidget(login)
        return sidebar

    def _select_nav(self, current: QPushButton, group: list[QPushButton]) -> None:
        for button in group:
            button.setChecked(button is current)

    def _build_upload_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 32, 34, 28)
        layout.setSpacing(18)

        title = QLabel("欢迎使用音频转文字")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        subtitle = QLabel("高效精准的语音识别，轻松将音频转换为文字")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #63708a;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.drop_zone = UploadDropZone()
        self.drop_zone.choose_button.clicked.connect(self._choose_file)
        self.drop_zone.file_dropped.connect(lambda value: self._set_file(Path(value)))
        layout.addWidget(self.drop_zone)

        feature_layout = QHBoxLayout()
        feature_layout.setSpacing(18)
        for title_text, body_text in [
            ("快速准确", "先进的 AI 语音识别技术，准确率高达 98%+"),
            ("安全可靠", "文件加密传输与存储，保护您的隐私安全"),
            ("多格式支持", "支持多种音频格式，满足不同需求"),
        ]:
            feature_layout.addWidget(self._feature_card(title_text, body_text))
        layout.addLayout(feature_layout)
        return card

    def _feature_card(self, title: str, body: str) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet("background: rgba(245, 248, 255, 0.82); border-radius: 12px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        icon = QLabel("◆")
        icon.setFixedSize(44, 44)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background:#edf3ff;color:#3f76ff;border-radius:10px;font-size:20px;")
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
        layout = QVBoxLayout(self.transcript_card)
        layout.setContentsMargins(22, 18, 22, 22)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("转录结果")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)
        copy_button = QPushButton("复制全文")
        copy_button.setObjectName("SecondaryButton")
        copy_button.clicked.connect(self._copy_transcript)
        header.addWidget(copy_button)
        open_button = QPushButton("打开文件夹")
        open_button.setObjectName("SecondaryButton")
        open_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir))))
        header.addWidget(open_button)
        layout.addLayout(header)
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setMinimumHeight(140)
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
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(22)
        heading = QLabel("转录设置")
        heading.setStyleSheet("font-size: 18px; font-weight: 800;")
        card_layout.addWidget(heading)

        self.language_combo = self._combo(["中文（普通话）", "自动识别", "English", "粤语"])
        self.model_combo = self._combo(["标准模型（推荐）", "精准模型"])
        self.speaker_check = ToggleSwitch()
        self.speaker_check.setEnabled(False)
        self.punctuation_check = ToggleSwitch()
        self.punctuation_check.setChecked(True)
        self.format_combo = self._combo(["TXT 文本格式", "Markdown", "SRT 字幕", "JSON 数据", "全部格式"])

        card_layout.addLayout(self._setting_row("语言", self.language_combo))
        card_layout.addLayout(self._setting_row("转录模型", self.model_combo))
        card_layout.addLayout(self._setting_row("说话人识别", self.speaker_check))
        card_layout.addLayout(self._setting_row("标点恢复", self.punctuation_check))
        card_layout.addLayout(self._setting_row("输出格式", self.format_combo))
        choose_output = QPushButton(f"保存位置：{self.output_dir}")
        choose_output.setObjectName("SecondaryButton")
        choose_output.clicked.connect(self._choose_output_dir)
        self.output_button = choose_output
        card_layout.addWidget(choose_output)
        layout.addWidget(card)

        self.start_button = QPushButton("开始转录")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_or_cancel)
        layout.addWidget(self.start_button)
        self.status_label = QLabel("请先上传音频文件")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #63708a;")
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addStretch(1)
        return panel

    def _combo(self, items: list[str]) -> QComboBox:
        combo = StyledComboBox()
        combo.addItems(items)
        return combo

    def _setting_row(self, label: str, control: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(QLabel(label))
        row.addStretch(1)
        control.setMinimumWidth(175)
        row.addWidget(control)
        return row

    def _build_recent_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("RecentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)
        title_row = QHBoxLayout()
        title = QLabel("最近文件")
        title.setStyleSheet("font-size: 18px; font-weight: 800;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        all_button = QPushButton("查看全部")
        all_button.setObjectName("SecondaryButton")
        title_row.addWidget(all_button)
        layout.addLayout(title_row)

        self.recent_table = QTableWidget(0, 6)
        self.recent_table.setHorizontalHeaderLabels(["文件名", "时长", "大小", "转录时间", "状态", "操作"])
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setShowGrid(False)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            self.recent_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.setMinimumHeight(142)
        layout.addWidget(self.recent_table)
        return card

    def _apply_theme(self) -> None:
        self.setStyleSheet(theme_stylesheet(self.theme_name))
        self.theme_button.setText("切换浅色" if self.theme_name is ThemeName.DARK else "切换深色")

    def _toggle_theme(self) -> None:
        self.theme_name = ThemeName.DARK if self.theme_name is ThemeName.LIGHT else ThemeName.LIGHT
        self.preferences = UserPreferences(theme=self.theme_name.value, output_dir=self.output_dir)
        save_preferences(self.preferences, self.preferences_path)
        self._apply_theme()

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
            self.output_button.setText(f"保存位置：{self.output_dir}")
            save_preferences(UserPreferences(theme=self.theme_name.value, output_dir=self.output_dir), self.preferences_path)

    def _selected_formats(self) -> tuple[str, ...]:
        value = self.format_combo.currentText()
        mapping = {
            "TXT 文本格式": ("txt",),
            "Markdown": ("md",),
            "SRT 字幕": ("srt",),
            "JSON 数据": ("json",),
            "全部格式": ("all",),
        }
        return mapping[value]

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

    def _on_progress(self, value: float, message: str) -> None:
        self.progress_bar.setValue(max(0, min(100, int(value * 100))))
        self.status_label.setText(message)

    def _on_completed(self, doc: TranscriptDocument, paths: list[Path]) -> None:
        self.last_doc = doc
        self.start_button.setText("重新转录")
        self.start_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText("转录完成")
        self.transcript_card.setVisible(True)
        self.transcript_text.setPlainText(export_txt(doc, self.punctuation_check.isChecked()))
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
        self.recent_table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item.file_path.name,
                item.duration_label,
                item.size_label,
                item.transcribed_at,
                item.status,
                "打开",
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 5:
                    table_item.setData(Qt.ItemDataRole.UserRole, str(item.output_dir))
                self.recent_table.setItem(row, column, table_item)
        self.recent_table.cellDoubleClicked.connect(self._open_history_output)

    def _open_history_output(self, row: int, _column: int) -> None:
        item = self.recent_table.item(row, 5)
        if item:
            QDesktopServices.openUrl(QUrl.fromLocalFile(item.data(Qt.ItemDataRole.UserRole)))

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
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
