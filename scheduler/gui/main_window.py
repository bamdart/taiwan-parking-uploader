"""
gui/main_window.py - 主視窗

組合 StatusPanel 與 LogViewer，提供選單列操作。
關閉視窗時彈出對話框詢問最小化或結束。

排版：
  ┌───────────────────────────────────────────────┐
  │ 選單列（檔案）                                 │
  ├───────────────────────────────────────────────┤
  │ ┌─城市卡片──┐ ┌─城市卡片──┐                   │
  │ └──────────┘ └──────────┘                     │
  │ ┌日誌─────────────────────────────────────┐   │
  │ └────────────────────────────────────────┘    │
  │ HITech 海姆達爾智慧科技 v1.0.1  🌐 ✉ L ▶    │
  │ 狀態列                       ☐ 開機自動啟動   │
  └───────────────────────────────────────────────┘
"""

import base64
import os
import subprocess
import sys
import webbrowser

from PySide6.QtCore import QByteArray, QSize, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from scheduler import branding
from scheduler.core import autostart

from . import brand
from .log_viewer import LogViewer
from .status_panel import StatusPanel
from .tray_icon import TrayIcon

# ------------------------------------------------------------------
# 公司資訊常數（集中於 scheduler/branding.py）
# ------------------------------------------------------------------

_COMPANY_NAME = branding.COMPANY_NAME
_WEBSITE_URL = branding.WEBSITE_URL
_EMAIL = branding.EMAIL
_LINE_URL = branding.LINE_URL
_YOUTUBE_URL = branding.YOUTUBE_URL

# ------------------------------------------------------------------
# 版號讀取
# ------------------------------------------------------------------


def _read_version() -> str:
    """回傳版號（單一來源：scheduler/branding.py 的 APP_VERSION）。"""
    return branding.APP_VERSION


# ------------------------------------------------------------------
# SVG Icons（base64 encoded 的 Lucide / Simple Icons 向量圖）
# ------------------------------------------------------------------

# Lucide Globe icon
_ICON_GLOBE_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IntDT0xPUn0iIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSIxMCIvPjxwYXRoIGQ9Ik0yIDEyaDIwIi8+PHBhdGggZD0iTTEyIDJhMTUuMyAxNS4zIDAgMCAxIDQgMTAgMTUuMyAxNS4zIDAgMCAxLTQgMTAgMTUuMyAxNS4zIDAgMCAxLTQtMTAgMTUuMyAxNS4zIDAgMCAxIDQtMTB6Ii8+PC9zdmc+"  # noqa: E501

# Lucide Mail icon
_ICON_MAIL_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IntDT0xPUn0iIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cmVjdCB3aWR0aD0iMjAiIGhlaWdodD0iMTYiIHg9IjIiIHk9IjQiIHJ4PSIyIi8+PHBhdGggZD0ibTIyIDctOC45NyA1LjdhMS45NCAxLjk0IDAgMCAxLTIuMDYgMEwyIDciLz48L3N2Zz4="  # noqa: E501

# Simple Icons LINE
_ICON_LINE_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ7Q09MT1J9Ij48cGF0aCBkPSJNMTkuMzY1IDkuODYzYy4zNDkgMCAuNjMuMjg1LjYzLjYzMSAwIC4zNDUtLjI4MS42My0uNjMuNjNIMTcuNjF2MS4xMjVoMS43NTVjLjM0OSAwIC42My4yODMuNjMuNjMgMCAuMzQ0LS4yODEuNjI5LS42My42MjloLTIuMzg2Yy0uMzQ1IDAtLjYyNy0uMjg1LS42MjctLjYyOVY4LjEwOGMwLS4zNDUuMjgyLS42My42My0uNjNoMi4zODZjLjM0NiAwIC42MjcuMjg1LjYyNy42MyAwIC4zNDktLjI4MS42My0uNjMuNjNIMTcuNjF2MS4xMjVoMS43NTV6bS0zLjg1NSAzLjAxNmMwIC4yNy0uMTc0LjUxLS40MzIuNTk2LS4wNjQuMDIxLS4xMzMuMDMxLS4xOTkuMDMxLS4yMTEgMC0uMzkxLS4wOS0uNTEtLjI1bC0yLjQ0My0zLjMxN3YyLjk0YzAgLjM0NC0uMjc5LjYyOS0uNjMxLjYyOS0uMzQ2IDAtLjYyNi0uMjg1LS42MjYtLjYyOVY4LjEwOGMwLS4yNy4xNzMtLjUxLjQzLS41OTUuMDYtLjAyMy4xMzYtLjAzMy4xOTQtLjAzMy4xOTUgMCAuMzc1LjEwNC40OTUuMjU0bDIuNDYyIDMuMzNWOC4xMDhjMC0uMzQ1LjI4Mi0uNjMuNjMtLjYzLjM0NSAwIC42My4yODUuNjMuNjN2NC43NzF6bS01Ljc0MSAwYzAgLjM0NC0uMjgyLjYyOS0uNjMxLjYyOS0uMzQ1IDAtLjYyNy0uMjg1LS42MjctLjYyOVY4LjEwOGMwLS4zNDUuMjgyLS42My42My0uNjMuMzQ2IDAgLjYyOC4yODUuNjI4LjYzdjQuNzcxem0tMi40NjYuNjI5SDQuOTE3Yy0uMzQ1IDAtLjYzLS4yODUtLjYzLS42MjlWOC4xMDhjMC0uMzQ1LjI4NS0uNjMuNjMtLjYzLjM0OCAwIC42My4yODUuNjMuNjN2NC4xNDFoMS43NTZjLjM0OCAwIC42MjkuMjgzLjYyOS42MyAwIC4zNDQtLjI4Mi42MjktLjYyOS42MjlNMjQgMTAuMzE0QzI0IDQuOTQzIDE4LjYxNS41NzIgMTIgLjU3MlMwIDQuOTQzIDAgMTAuMzE0YzAgNC44MTEgNC4yNyA4Ljg0MiAxMC4wMzUgOS42MDguMzkxLjA4Mi45MjMuMjU4IDEuMDU4LjU5LjEyLjMwMS4wNzkuNzY2LjAzOCAxLjA4bC0uMTY0IDEuMDJjLS4wNDUuMzAxLS4yNCAxLjE4NiAxLjA0OS42NDUgMS4yOTEtLjUzOSA2LjkxNi00LjA3OCA5LjQzNi02Ljk3NUMyMy4xNzYgMTQuMzkzIDI0IDEyLjQ1OCAyNCAxMC4zMTQiLz48L3N2Zz4="  # noqa: E501

# Simple Icons YouTube
_ICON_YOUTUBE_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ7Q09MT1J9Ij48cGF0aCBkPSJNMjMuNDk4IDYuMTg2YTMuMDE2IDMuMDE2IDAgMCAwLTIuMTIyLTIuMTM2QzE5LjUwNSAzLjU0NSAxMiAzLjU0NSAxMiAzLjU0NXMtNy41MDUgMC05LjM3Ny41MDVBMy4wMTcgMy4wMTcgMCAwIDAgLjUwMiA2LjE4NkMwIDguMDcgMCAxMiAwIDEyczAgMy45My41MDIgNS44MTRhMy4wMTYgMy4wMTYgMCAwIDAgMi4xMjIgMi4xMzZjMS44NzEuNTA1IDkuMzc2LjUwNSA5LjM3Ni41MDVzNy41MDUgMCA5LjM3Ny0uNTA1YTMuMDE1IDMuMDE1IDAgMCAwIDIuMTIyLTIuMTM2QzI0IDE1LjkzIDI0IDEyIDI0IDEyczAtMy45My0uNTAyLTUuODE0ek05LjU0NSAxNS41NjhWOC40MzJMMTUuODE4IDEybC02LjI3MyAzLjU2OHoiLz48L3N2Zz4="  # noqa: E501


def _svg_icon(b64_data: str, color: str, size: int = 20) -> QIcon:
    """從 base64 SVG 建立 QIcon，將 {COLOR} placeholder 替換為指定色彩。"""
    svg_bytes = base64.b64decode(b64_data)
    svg_str = svg_bytes.decode("utf-8").replace("{COLOR}", color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    from PySide6.QtGui import QPainter
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# ------------------------------------------------------------------
# 連結按鈕樣式
# ------------------------------------------------------------------


def _link_btn_qss() -> str:
    """依主題產生連結按鈕樣式。"""
    t = brand.get_theme()
    return f"""
QPushButton {{
    border: none;
    background: transparent;
    padding: 4px;
    border-radius: 4px;
}}
QPushButton:hover {{
    background: {t['surface_alt']};
}}
"""



class MainWindow(QMainWindow):
    """主視窗。"""

    # 清除資料並重新設定
    reset_requested = Signal()

    def __init__(
        self,
        visible_cities: list[str],
        on_quit,
        base_dir: str,
        config_manager=None,
        parent=None,
    ):
        super().__init__(parent)
        self._on_quit = on_quit
        self._base_dir = base_dir
        self._config = config_manager

        version = _read_version()
        title = branding.APP_NAME
        if version:
            title += f" v{version}"
        self.setWindowTitle(title)
        self.setMinimumSize(500, 420)
        self.resize(700, 620)

        # 設定視窗圖示（從內嵌 base64）
        from ._favicon import favicon_qicon
        self.setWindowIcon(favicon_qicon())

        # 選單列
        self._build_menu_bar()

        # 中央 widget
        central = QWidget()
        layout = QVBoxLayout()

        # 狀態面板（可編輯卡片）
        self._status_panel = StatusPanel(visible_cities)
        layout.addWidget(self._status_panel)

        # Log 顯示
        self._log_viewer = LogViewer()
        layout.addWidget(self._log_viewer, stretch=1)

        # 公司資訊列
        layout.addWidget(self._build_company_bar())

        central.setLayout(layout)
        self.setCentralWidget(central)

        # 狀態列
        self._status_bar = QStatusBar()

        # 目前時間（左下角），每秒更新
        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            f"color: {brand.get_theme()['text_muted']}; "
            f"font-family: 'Consolas', 'Courier New', monospace; "
            f"font-size: {brand.get_font_sizes()['small']}px; "
            f"padding: 0 8px;"
        )
        self._status_bar.addWidget(self._clock_label)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # 開機自啟動 checkbox（右下角）
        self._autostart_checkbox = QCheckBox("開機自動啟動")
        self._autostart_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        if autostart.is_supported():
            self._autostart_checkbox.setChecked(autostart.is_enabled())
            self._autostart_checkbox.toggled.connect(self._on_autostart_toggled)
        else:
            self._autostart_checkbox.setEnabled(False)
            self._autostart_checkbox.setToolTip("僅編譯後的 .exe 支援此功能")
        self._status_bar.addPermanentWidget(self._autostart_checkbox)

        self.setStatusBar(self._status_bar)

        # Tray icon
        self._tray = TrayIcon(self, on_quit)
        self._tray.show()

    # ------------------------------------------------------------------
    # Company info bar
    # ------------------------------------------------------------------

    def _build_company_bar(self) -> QWidget:
        """建立公司資訊列（字級隨 brand 動態調整）。"""
        s = brand.get_font_sizes()
        t = brand.get_theme()

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        # 分隔線
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {t['divider']};")
        layout.addWidget(separator)

        # 公司名稱（字級/顏色由全域 QSS QLabel#companyLabel 控制）
        name_row = QHBoxLayout()
        name_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        company_label = QLabel(_COMPANY_NAME)
        company_label.setObjectName("companyLabel")
        name_row.addWidget(company_label)

        layout.addLayout(name_row)

        # 社群連結列（SVG icon 按鈕，icon 與按鈕大小隨字級）
        links_row = QHBoxLayout()
        links_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        links_row.setSpacing(4)

        normal_color = t['text_muted']
        hover_color = brand.PRIMARY_2

        icon_px = s['icon']
        btn_px = icon_px + 10  # 按鈕略大於 icon
        icon_size = QSize(icon_px, icon_px)

        links = [
            ("官網", _ICON_GLOBE_B64, _WEBSITE_URL),
            (f"Email: {_EMAIL}", _ICON_MAIL_B64, f"mailto:{_EMAIL}"),
            ("LINE", _ICON_LINE_B64, _LINE_URL),
            ("YouTube", _ICON_YOUTUBE_B64, _YOUTUBE_URL),
        ]

        for tooltip, icon_b64, url in links:
            btn = QPushButton()
            btn.setToolTip(tooltip)
            btn.setIcon(_svg_icon(icon_b64, normal_color, icon_px))
            btn.setIconSize(icon_size)
            btn.setFixedSize(btn_px, btn_px)
            btn.setStyleSheet(_link_btn_qss())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # Hover 時換色 icon
            _url = url  # closure capture
            _b64 = icon_b64
            _px = icon_px
            btn.clicked.connect(lambda checked=False, u=_url: webbrowser.open(u))
            btn.enterEvent = lambda event, b=btn, d=_b64, p=_px: b.setIcon(
                _svg_icon(d, hover_color, p)
            )
            btn.leaveEvent = lambda event, b=btn, d=_b64, p=_px: b.setIcon(
                _svg_icon(d, normal_color, p)
            )

            links_row.addWidget(btn)

        layout.addLayout(links_row)

        container.setLayout(layout)
        return container

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        settings_menu = menu_bar.addMenu("設定(&S)")

        act_open_logs = QAction("開啟記錄檔資料夾", self)
        act_open_logs.triggered.connect(self._open_logs_folder)
        settings_menu.addAction(act_open_logs)

        settings_menu.addSeparator()

        # 字體大小子選單
        font_menu = settings_menu.addMenu("字體大小")
        current_font = self._config.font_size if self._config else "standard"
        self._font_actions: dict[str, QAction] = {}
        for key, preset in brand.FONT_SIZE_PRESETS.items():
            label = preset["label"]
            if key == current_font:
                label += " ✓"
            act = QAction(label, self)
            act.setData(key)
            act.triggered.connect(lambda checked=False, k=key: self._on_font_size_changed(k))
            font_menu.addAction(act)
            self._font_actions[key] = act

        # 主題子選單
        theme_menu = settings_menu.addMenu("主題")
        current_theme = self._config.theme if self._config else "system"
        self._theme_actions: dict[str, QAction] = {}
        theme_options = [
            ("system", "跟隨系統"),
            ("light", "明亮"),
            ("dark", "黑暗"),
        ]
        for key, label_text in theme_options:
            label = label_text
            if key == current_theme:
                label += " ✓"
            act = QAction(label, self)
            act.setData(key)
            act.triggered.connect(lambda checked=False, k=key: self._on_theme_changed(k))
            theme_menu.addAction(act)
            self._theme_actions[key] = act

        settings_menu.addSeparator()

        act_reset = QAction("清除資料並重新設定", self)
        act_reset.triggered.connect(self._on_reset)
        settings_menu.addAction(act_reset)

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _update_clock(self) -> None:
        """更新左下角的目前時間顯示（HH:MM:SS）。"""
        self._clock_label.setText(
            f"現在時間 {QTime.currentTime().toString('HH:mm:ss')}"
        )

    def _open_logs_folder(self) -> None:
        logs_dir = os.path.join(self._base_dir, "logs")
        if not os.path.isdir(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        self._open_file(logs_dir)

    def _on_reset(self) -> None:
        reply = QMessageBox.question(
            self,
            "清除資料並重新設定",
            "確定要清除所有設定嗎？\n\n"
            "這將刪除 .env 和 schedule.json，\n"
            "並重新啟動設定精靈。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_requested.emit()

    def _on_font_size_changed(self, key: str) -> None:
        """切換字體大小，存入 .env 並提示重啟。"""
        if not self._config:
            return
        preset_label = brand.FONT_SIZE_PRESETS[key]["label"]
        reply = QMessageBox.question(
            self,
            "字體大小調整",
            f"字體大小將設為「{preset_label}」。\n\n需要重新啟動程式才能完整套用。\n確定要立即重啟嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._config.update_env_value("FONT_SIZE", key)
        self._restart_app()

    def _on_theme_changed(self, key: str) -> None:
        """切換主題，存入 .env 並提示重啟。"""
        if not self._config:
            return
        labels = {"system": "跟隨系統", "light": "明亮", "dark": "黑暗"}
        reply = QMessageBox.question(
            self,
            "主題調整",
            f"主題將設為「{labels[key]}」。\n\n需要重新啟動程式才能完整套用。\n確定要立即重啟嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._config.update_env_value("THEME", key)
        self._restart_app()

    def _restart_app(self) -> None:
        """重新啟動本程式。

        使用中繼的 cmd 延遲啟動，確保舊程序完全結束（釋放 lock、清理 PyInstaller
        temp 解壓目錄）後，新程序才開始解壓與載入模組。

        關鍵：清除子程序環境中的 PyInstaller runtime 變數。否則子程序的
        bootloader 會誤判「已經解壓過」而去找父程序的 _MEI 目錄（已被刪除），
        導致 python310.dll 載入失敗或 base_library.zip 找不到。
        """
        self._tray.hide()
        self.hide()

        exe_path = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]

        # 清除 PyInstaller 相關環境變數，避免子程序繼承導致 bootloader 混亂
        child_env = os.environ.copy()
        for key in list(child_env.keys()):
            if (
                key.startswith("_PYI_")
                or key.startswith("_MEI")
                or key in ("_PYINSTALLER_RUNTIME_INFO", "PYINSTALLER_RESET_ENVIRONMENT")
            ):
                child_env.pop(key, None)

        try:
            if sys.platform == "win32":
                # cmd 延遲 2 秒再啟動 exe，給舊程序足夠時間完全退出
                if getattr(sys, "frozen", False):
                    cmd = f'timeout /t 2 /nobreak >nul & start "" "{exe_path}"'
                else:
                    py = sys.executable
                    cmd = f'timeout /t 2 /nobreak >nul & start "" "{py}" "{exe_path}"'
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    cmd,
                    shell=True,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
                    close_fds=True,
                    env=child_env,
                )
            else:
                args = [exe_path] if getattr(sys, "frozen", False) else [sys.executable, exe_path]
                cmd = f'sleep 2 && exec "{" ".join(args)}"'
                subprocess.Popen(
                    ["bash", "-c", cmd],
                    start_new_session=True,
                    close_fds=True,
                    env=child_env,
                )
        except OSError as e:
            QMessageBox.warning(self, "重啟失敗", f"無法重新啟動程式：\n{e}")
            return

        # 呼叫 on_quit 釋放 lock 並結束
        self._on_quit()

    @staticmethod
    def _open_file(path: str) -> None:
        """用系統預設程式開啟檔案或目錄。"""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def status_panel(self) -> StatusPanel:
        return self._status_panel

    @property
    def log_viewer(self) -> LogViewer:
        return self._log_viewer

    @property
    def tray(self) -> TrayIcon:
        return self._tray

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def set_status_text(self, text: str) -> None:
        """保留方法以相容外部呼叫（不再顯示 UI）。"""
        pass

    # ------------------------------------------------------------------
    # 開機自啟動 checkbox
    # ------------------------------------------------------------------

    def _on_autostart_toggled(self, checked: bool) -> None:
        if checked:
            success, message = autostart.enable()
        else:
            success, message = autostart.disable()

        if not success:
            self._autostart_checkbox.blockSignals(True)
            self._autostart_checkbox.setChecked(autostart.is_enabled())
            self._autostart_checkbox.blockSignals(False)
            QMessageBox.warning(self, "開機自動啟動", message)
        else:
            self._tray.showMessage(
                branding.APP_NAME,
                message,
                self._tray.MessageIcon.Information,
                3000,
            )

    # ------------------------------------------------------------------
    # Close → 詢問最小化或結束
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._tray.isVisible():
            event.accept()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("關閉程式")
        msg.setText("上傳系統仍在運行中")
        msg.setInformativeText("要最小化到系統匣繼續背景執行，還是結束程式？")
        msg.setIcon(QMessageBox.Icon.Question)

        btn_minimize = msg.addButton("最小化到系統匣", QMessageBox.ButtonRole.AcceptRole)
        btn_quit = msg.addButton("結束程式", QMessageBox.ButtonRole.DestructiveRole)
        # 隱藏的取消按鈕：作為 X / Esc 的觸發目標，讓 clickedButton() 不回傳 None
        btn_cancel = msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        btn_cancel.hide()
        msg.setDefaultButton(btn_minimize)
        msg.setEscapeButton(btn_cancel)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_minimize:
            self.hide()
            event.ignore()
        elif clicked == btn_quit:
            event.ignore()
            self._on_quit()
        else:
            # 使用者按右上角 X 或 Esc → 視為取消，關閉對話框、保持主視窗
            event.ignore()
