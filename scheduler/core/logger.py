"""
core/logger.py - JSONL log manager

遵循專案 log standard：ISO 8601 含時區偏移、毫秒精度、camelCase data keys。
Log 檔案存放於 logs/ 子資料夾，每日一檔 scheduler-YYYY-MM-DD.jsonl。
"""

import json
import os
import re
from collections import deque
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal


class LogManager(QObject):
    """JSONL log 管理器，含內存 ring buffer 供 GUI 即時顯示。"""

    log_entry_added = Signal(dict)

    _BUFFER_SIZE = 500
    _LOG_PREFIX = "scheduler-"
    _LOG_SUFFIX = ".jsonl"

    def __init__(self, base_dir: str, retention_days: int = 90, parent=None):
        super().__init__(parent)
        self._log_dir = os.path.join(base_dir, "logs")
        self._retention_days = retention_days
        self._buffer: deque[dict] = deque(maxlen=self._BUFFER_SIZE)

        os.makedirs(self._log_dir, exist_ok=True)

        # 啟動時清理過期 log
        self._clean_old_logs()

        # 每日 00:00:30 清理排程
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._schedule_daily_cleanup)
        self._start_daily_cleanup_timer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_retention_days(self, days: int) -> None:
        self._retention_days = days

    def info(self, message: str, data: dict | None = None) -> None:
        self._write("info", message, data)

    def warn(self, message: str, data: dict | None = None) -> None:
        self._write("warn", message, data)

    def error(self, message: str, data: dict | None = None) -> None:
        self._write("error", message, data)

    def debug(self, message: str, data: dict | None = None) -> None:
        self._write("debug", message, data)

    def get_buffer(self) -> list[dict]:
        """回傳內存 buffer 的複本。"""
        return list(self._buffer)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, level: str, message: str, data: dict | None) -> None:
        entry = {
            "time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "level": level,
            "message": message,
        }
        if data:
            entry["data"] = data

        # 寫入檔案
        line = json.dumps(entry, ensure_ascii=False)
        log_path = self._today_log_path()
        try:
            with open(log_path, "a", encoding="utf-8", newline="") as f:
                f.write(line + "\n")
        except OSError:
            pass

        # 加入 buffer 並通知 GUI
        self._buffer.append(entry)
        self.log_entry_added.emit(entry)

    def _today_log_path(self) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(
            self._log_dir, f"{self._LOG_PREFIX}{date_str}{self._LOG_SUFFIX}"
        )

    def _clean_old_logs(self) -> None:
        if not os.path.isdir(self._log_dir):
            return

        cutoff = datetime.now() - timedelta(days=self._retention_days)
        pattern = re.compile(
            rf"^{re.escape(self._LOG_PREFIX)}(\d{{4}}-\d{{2}}-\d{{2}}){re.escape(self._LOG_SUFFIX)}$"
        )

        for filename in os.listdir(self._log_dir):
            m = pattern.match(filename)
            if not m:
                continue
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                continue
            if file_date < cutoff:
                try:
                    os.remove(os.path.join(self._log_dir, filename))
                except OSError:
                    pass

    def _start_daily_cleanup_timer(self) -> None:
        """計算到明天 00:00:30 的延遲，啟動 single-shot timer。"""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=30, microsecond=0
        )
        delay_ms = int((tomorrow - now).total_seconds() * 1000)
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.start(delay_ms)

    def _schedule_daily_cleanup(self) -> None:
        self._clean_old_logs()
        self._start_daily_cleanup_timer()
