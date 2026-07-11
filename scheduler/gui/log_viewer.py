"""
gui/log_viewer.py - JSONL log 即時顯示器

唯讀 QTextEdit，依 level 色彩標記，自動捲到底部。
字級隨 brand.get_font_sizes() 動態調整。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from scheduler.gui import brand

# GUI 日誌不顯示的技術欄位（這些仍會寫入 JSONL 檔案供除錯）
_HIDDEN_DATA_KEYS = {
    "endpoint",
    "soapAction",
    "statusCode",
    "responseBody",
    "requestBody",
    "err",
    "target",  # 訊息中已有縣市名稱
    "schedule",
}

_LEVEL_LABELS = {
    "debug": "除錯",
    "info": "訊息",
    "warn": "注意",
    "error": "錯誤",
    "fatal": "嚴重錯誤",
}


class LogViewer(QWidget):
    """Log 顯示面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 標題列（字級/顏色由全域 QSS QLabel#logTitle 控制）
        title = QLabel("日誌")
        title.setObjectName("logTitle")
        layout.addWidget(title)

        # Log 文字區（monospace，字級由全域 QSS QTextEdit 控制）
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(
            "QTextEdit { font-family: 'Consolas', 'Courier New', monospace; }"
        )
        layout.addWidget(self._text, stretch=1)

        # 底部工具列：清除日誌按鈕靠右，紅色樣式
        footer = QHBoxLayout()
        footer.addStretch()
        clear_btn = QPushButton("清除日誌")
        clear_btn.setStyleSheet(brand.BTN_DANGER)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear)
        footer.addWidget(clear_btn)
        layout.addLayout(footer)

        self.setLayout(layout)

    def append_entry(self, entry: dict) -> None:
        """新增一筆 log entry。"""
        time_str = entry.get("time", "")
        level = entry.get("level", "info")
        message = entry.get("message", "")
        data = entry.get("data")

        theme = brand.get_theme()
        color = brand.LOG_COLORS.get(level, theme['text'])
        muted = theme['text_muted']
        time_short = time_str[11:19] if len(time_str) > 19 else time_str
        level_label = _LEVEL_LABELS.get(level, level.upper())

        # 訊息可能含換行，轉成 HTML br
        safe_message = message.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        html = (
            f'<span style="color:{muted}">{time_short}</span> '
            f'<span style="color:{color};font-weight:bold">[{level_label}]</span> '
            f'<span style="color:{theme["text"]}">{safe_message}</span>'
        )

        # 只顯示使用者關心的欄位，過濾技術性 key
        if data:
            visible_items = {
                k: v for k, v in data.items() if k not in _HIDDEN_DATA_KEYS
            }
            if visible_items:
                data_str = " ".join(f"{k}={v}" for k, v in visible_items.items())
                html += f' <span style="color:{muted}">{data_str}</span>'

        self._text.append(html)

        # 自動捲到底部
        scrollbar = self._text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def load_buffer(self, entries: list[dict]) -> None:
        """載入既有 buffer。"""
        for entry in entries:
            self.append_entry(entry)

    def _clear(self) -> None:
        self._text.clear()
