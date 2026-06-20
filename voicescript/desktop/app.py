from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from voicescript.backends.qwen_backend import QWEN_MODEL_KEY
from voicescript.backends.whisper_backend import WHISPER_MODEL_KEY
from voicescript.core.audio import SUPPORTED_AUDIO_EXTENSIONS, is_supported_audio_file
from voicescript.core.environment import check_environment
from voicescript.core.exporters import export_transcript, format_clock
from voicescript.core.settings import default_settings
from voicescript.core.transcript import Transcript
from voicescript.desktop.theme import ThemeMode, build_stylesheet
from voicescript.desktop.worker import TranscriptionWorker


class DropZone(QFrame):
    file_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(132)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        title = QLabel("拖入音频文件，或点击左侧选择")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        subtitle = QLabel("支持 m4a / caf / aac / amr / 3gp / ogg / opus / mp3 / wav / flac")
        subtitle.setObjectName("Muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            path = Path(event.mimeData().urls()[0].toLocalFile())
            if is_supported_audio_file(path):
                event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if is_supported_audio_file(path):
                self.file_selected.emit(path)


class MainWindow(QMainWindow):
    def __init__(self, *, auto_start_on_file_select: bool = True) -> None:
        super().__init__()
        self.settings = default_settings()
        self.auto_start_on_file_select = auto_start_on_file_select
        self.theme_mode = ThemeMode.BLACK
        self.audio_path: Path | None = None
        self.transcript: Transcript | None = None
        self.worker: TranscriptionWorker | None = None
        self.setWindowTitle("VoiceScript 声笺录")
        self.resize(1180, 760)
        self._build_ui()
        self._apply_theme()
        self._refresh_environment()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(20, 20, 20, 12)
        shell.setSpacing(16)

        side = QFrame()
        side.setObjectName("ChromePanel")
        side.setFixedWidth(316)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(20, 20, 20, 20)
        side_layout.setSpacing(12)

        brand = QLabel("声笺录")
        brand.setObjectName("Brand")
        motto = QLabel("VoiceScript · 声落成笺，语转为文")
        motto.setObjectName("Motto")
        side_layout.addWidget(brand)
        side_layout.addWidget(motto)
        side_layout.addSpacing(12)

        self.file_label = QLabel("尚未选择音频")
        self.file_label.setWordWrap(True)
        self.file_label.setObjectName("Muted")

        self.choose_button = QPushButton("选择音频")
        self.choose_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.choose_button.clicked.connect(self._choose_file)

        self.model_combo = QComboBox()
        self.model_combo.addItem("Whisper large-v3", WHISPER_MODEL_KEY)
        self.model_combo.addItem("Qwen3-ASR-1.7B", QWEN_MODEL_KEY)

        self.theme_button = QPushButton("切换白色模式")
        self.theme_button.clicked.connect(self._toggle_theme)

        self.start_button = QPushButton("开始转录")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.start_button.clicked.connect(self._start_transcription)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop))
        self.cancel_button.clicked.connect(self._cancel_transcription)

        self.export_button = QPushButton("导出文件")
        self.export_button.setEnabled(False)
        self.export_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.export_button.clicked.connect(self._export_files)

        self.obsidian_button = QPushButton("保存到 Obsidian")
        self.obsidian_button.setEnabled(False)
        self.obsidian_button.clicked.connect(self._save_to_obsidian)

        self.env_label = QLabel("")
        self.env_label.setWordWrap(True)
        self.env_label.setObjectName("Muted")

        for widget in [
            self.file_label,
            self.choose_button,
            self.model_combo,
            self.theme_button,
            self.start_button,
            self.cancel_button,
            self.export_button,
            self.obsidian_button,
        ]:
            side_layout.addWidget(widget)
        side_layout.addStretch(1)
        side_layout.addWidget(QLabel("运行环境"))
        side_layout.addWidget(self.env_label)

        main = QFrame()
        main.setObjectName("ContentSurface")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        self.drop_zone = DropZone()
        self.drop_zone.file_selected.connect(self._set_audio_file)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.status_label = QLabel("请选择一个完整音频文件。")
        self.status_label.setObjectName("Muted")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["开始", "结束", "完整文字"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)

        top_grid = QGridLayout()
        top_grid.addWidget(self.drop_zone, 0, 0, 1, 2)
        main_layout.addLayout(top_grid)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.table, 1)

        shell.addWidget(side)
        shell.addWidget(main, 1)

        self.setStatusBar(QStatusBar())
        refresh_action = QAction("Refresh Environment", self)
        refresh_action.triggered.connect(self._refresh_environment)
        self.addAction(refresh_action)

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self.theme_mode))
        self.theme_button.setText("切换黑色模式" if self.theme_mode == ThemeMode.WHITE else "切换白色模式")

    def _toggle_theme(self) -> None:
        self.theme_mode = ThemeMode.WHITE if self.theme_mode == ThemeMode.BLACK else ThemeMode.BLACK
        self._apply_theme()

    def _refresh_environment(self) -> None:
        report = check_environment(self.settings.cache_dir)
        warnings = report.warnings
        gpu = report.torch.cuda_device or "CPU"
        memory = f"{report.torch.cuda_memory_gb}GB" if report.torch.cuda_memory_gb else "未知显存"
        self.env_label.setText(
            f"ffmpeg: {'OK' if report.ffmpeg.available else '缺失'}\n"
            f"ffprobe: {'OK' if report.ffprobe.available else '缺失'}\n"
            f"Torch/CUDA: {gpu} / {memory}\n"
            + ("\n".join(warnings) if warnings else "环境检查未发现阻断项。")
        )

    def _choose_file(self) -> None:
        extensions = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_AUDIO_EXTENSIONS))
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择完整音频文件",
            str(Path.home()),
            f"Audio Files ({extensions})",
        )
        if filename:
            self._set_audio_file(Path(filename))

    def _set_audio_file(self, path: Path) -> None:
        if not is_supported_audio_file(path):
            QMessageBox.warning(self, "格式不支持", f"暂不支持该格式：{path.suffix}")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "正在转录", "当前转录任务仍在运行，请先取消或等待完成。")
            return
        self.audio_path = Path(path)
        self.transcript = None
        self.file_label.setText(str(self.audio_path))
        self.status_label.setText("音频已选择，正在启动转录任务。")
        self.export_button.setEnabled(False)
        self.obsidian_button.setEnabled(False)
        self.table.setRowCount(0)
        if self.auto_start_on_file_select:
            self._start_transcription()

    def _start_transcription(self) -> None:
        if not self.audio_path:
            QMessageBox.information(self, "需要音频", "请先选择或拖入一个完整音频文件。")
            return
        if self.worker and self.worker.isRunning():
            return
        self.progress.setValue(0)
        self.table.setRowCount(0)
        self.status_label.setText("准备加载模型。首次使用会下载模型权重。")
        self._set_running(True)
        self.worker = TranscriptionWorker(self.model_combo.currentData(), self.audio_path)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _cancel_transcription(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("正在取消转录任务。")

    def _on_progress(self, message: str, value) -> None:
        self.status_label.setText(message)
        if isinstance(value, (int, float)):
            next_value = max(0, min(100, int(float(value) * 100)))
            self.progress.setValue(max(self.progress.value(), next_value))

    def _on_completed(self, transcript: Transcript) -> None:
        self.transcript = transcript
        self._render_transcript(transcript)
        self.progress.setValue(100)
        self.status_label.setText("转录完成。内容保持原始转录，不做总结。")
        self.statusBar().showMessage("Transcription ready", 5000)
        self._set_running(False)
        self.export_button.setEnabled(True)
        self.obsidian_button.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        self.status_label.setText(message)
        QMessageBox.warning(self, "转录未完成", message)

    def _set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.choose_button.setEnabled(not running)
        self.model_combo.setEnabled(not running)

    def _render_transcript(self, transcript: Transcript) -> None:
        self.table.setRowCount(len(transcript.segments))
        for row, segment in enumerate(transcript.segments):
            values = [format_clock(segment.start), format_clock(segment.end), segment.text]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
        self.table.resizeRowsToContents()

    def _export_files(self) -> None:
        if not self.transcript:
            return
        directory = QFileDialog.getExistingDirectory(self, "选择导出文件夹", str(self.settings.default_export_dir))
        if not directory:
            return
        paths = export_transcript(self.transcript, Path(directory))
        self.statusBar().showMessage(f"Exported {len(paths)} files to {directory}", 6000)

    def _save_to_obsidian(self) -> None:
        if not self.transcript:
            return
        paths = export_transcript(self.transcript, self.settings.obsidian_dir, formats=("md", "json"))
        self.statusBar().showMessage(f"Saved to Obsidian: {paths['md']}", 7000)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
