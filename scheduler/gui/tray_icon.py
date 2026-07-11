"""
gui/tray_icon.py - 系統匣圖示

QSystemTrayIcon 封裝：右鍵選單（顯示/結束）、左鍵 toggle、tooltip 狀態。
圖示從內嵌 base64（_favicon.py）載入，避免 PyInstaller 臨時檔問題。
"""

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from scheduler import branding

from ._favicon import favicon_qicon


class TrayIcon(QSystemTrayIcon):
    """系統匣圖示，支援 toggle 視窗、結束。"""

    def __init__(self, main_window, on_quit, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._on_quit = on_quit

        # 圖示（從內嵌 base64 載入，fallback 到 Qt 標準 icon）
        icon = self._load_icon()
        self.setIcon(icon)
        self.setToolTip(branding.APP_NAME)

        # 右鍵選單
        menu = QMenu()
        action_show = QAction("顯示視窗", menu)
        action_show.triggered.connect(self._show_window)
        menu.addAction(action_show)

        menu.addSeparator()

        action_quit = QAction("結束", menu)
        action_quit.triggered.connect(self._on_quit)
        menu.addAction(action_quit)

        self.setContextMenu(menu)

        # 左鍵點擊 toggle
        self.activated.connect(self._on_activated)

    def update_tooltip(self, status: str) -> None:
        status_text = {"ok": "正常", "warning": "部分異常", "error": "上傳失敗"}
        label = status_text.get(status, status)
        self.setToolTip(f"{branding.APP_NAME} — {label}")

    def _show_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._main_window.isVisible():
                self._main_window.hide()
            else:
                self._show_window()

    @staticmethod
    def _load_icon() -> QIcon:
        """從內嵌 base64 載入 ICO 圖示，失敗則用 Qt 標準 icon。"""
        try:
            icon = favicon_qicon()
            if not icon.isNull():
                return icon
        except Exception:
            pass
        app = QApplication.instance()
        if app:
            return app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        return QIcon()

    @staticmethod
    def _find_icon() -> str | None:
        """相容舊 API：回傳 None（圖示已改為內嵌，不再有檔案路徑）。"""
        return None
