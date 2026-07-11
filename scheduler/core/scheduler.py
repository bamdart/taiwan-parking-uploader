"""
core/scheduler.py - 排程引擎

單一 QTimer 每分鐘 :00 秒觸發，檢查哪些工作需要執行。
上傳透過 QThreadPool 非阻塞執行。

本檔不含縣市專屬邏輯：要跑哪些縣市、如何解讀結果，一律向 scheduler.cities
註冊表查詢。
"""

from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from scheduler import cities

from . import net_errors
from .uploader import upload


def _short_name(target: str) -> str:
    """縣市訊息用短名，找不到外掛時回傳 target。"""
    plugin = cities.get_city(target)
    return plugin.short_name if plugin else target


class _UploadWorker(QRunnable):
    """在背景執行 HTTP POST 的 worker。"""

    class Signals(QObject):
        finished = Signal(str, dict)  # target, full result dict

    def __init__(self, target: str, config: dict):
        super().__init__()
        self._target = target
        self._config = config
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self) -> None:
        result = upload(self._config)
        self.signals.finished.emit(self._target, result)


class SchedulerEngine(QObject):
    """每分鐘 tick 的排程引擎。"""

    # (target, success, message)
    upload_completed = Signal(str, bool, str)
    # (target, next_time_iso)
    next_upload_changed = Signal(str, str)
    # "ok" | "warning" | "error"
    status_changed = Signal(str)

    def __init__(self, config_manager=None, logger=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._logger = logger
        self._schedule: dict | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._thread_pool = QThreadPool.globalInstance()

        # 各城市狀態
        self._city_status: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Signals for GUI
    # ------------------------------------------------------------------

    # 設定有變更時通知 GUI 更新面板
    config_reloaded = Signal(dict)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, schedule: dict) -> None:
        """設定排程並啟動。啟動時不立即上傳，等到下一個對齊時間才執行。"""
        self._schedule = schedule
        self._update_city_status()
        self._started = True

        # 啟動 timer：先對齊到下一個 :00 秒，之後每 60 秒 tick
        self._start_aligned_timer()

    def stop(self) -> None:
        """停止排程。"""
        self._timer.stop()
        self._started = False

    def is_started(self) -> bool:
        """是否已啟動。"""
        return getattr(self, "_started", False)

    def get_city_status(self, target: str) -> dict:
        return self._city_status.get(target, {})

    def upload_now(self, target: str) -> None:
        """立即觸發指定城市的上傳（略過時間對齊，供手動上傳使用）。"""
        if not self._schedule:
            return
        city_config = self._schedule.get(target)
        if not city_config:
            return
        self._submit_upload(target, city_config)

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    def _start_aligned_timer(self) -> None:
        """計算到下一個整分鐘 :00 秒的延遲，single-shot 啟動。"""
        now = datetime.now()
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        delay_ms = int((next_minute - now).total_seconds() * 1000)
        # 先用 single-shot 對齊到 :00
        QTimer.singleShot(delay_ms, self._on_first_tick)

    def _on_first_tick(self) -> None:
        self._on_tick()
        # 之後每 60 秒 tick
        self._timer.start(60_000)

    def _on_tick(self) -> None:
        # 每次 tick 都重新讀取 schedule.json，確保 enabled 狀態即時反映
        self._refresh_schedule()
        if not self._schedule:
            return
        self._execute_all()

    def _refresh_schedule(self) -> None:
        """從 ConfigManager 重讀 schedule.json。"""
        if not self._config:
            return
        changed = self._config.reload()
        if changed:
            new_schedule = self._config.schedule
            if new_schedule:
                self._schedule = new_schedule
                self._update_city_status()
                if self._logger:
                    self._logger.info("偵測到設定變更，已自動重新載入")
                self.config_reloaded.emit(new_schedule)
            elif self._schedule:
                # schedule.json 被刪除
                self._schedule = None
                if self._logger:
                    self._logger.warn("設定檔已被刪除，排程暫停")

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def _execute_all(self, force: bool = False) -> None:
        """執行上傳。force=True 時跳過時間對齊檢查（啟動時使用）。"""
        if not self._schedule:
            return

        now = datetime.now()
        minutes_since_midnight = now.hour * 60 + now.minute

        for target in cities.city_keys():
            city_config = self._schedule.get(target)
            if not city_config or not city_config.get("enabled"):
                continue

            interval = city_config.get("intervalMinutes", 10)
            if interval <= 0:
                continue

            # 非強制模式下才檢查時間對齊
            if not force and not self._should_execute(minutes_since_midnight, interval):
                continue

            self._submit_upload(target, city_config)

            # 計算下次執行時間
            next_time = self._calc_next_time(interval)
            self._city_status.setdefault(target, {})["nextUpload"] = next_time.isoformat()
            self.next_upload_changed.emit(target, next_time.isoformat())

    def _should_execute(self, minutes_since_midnight: int, interval: int) -> bool:
        return minutes_since_midnight % interval == 0

    def _submit_upload(self, target: str, config: dict) -> None:
        if self._logger:
            display_label = config.get("displayLabel", "")
            city = _short_name(target)
            msg = f"開始上傳 {city}"
            if display_label:
                msg += f"（{display_label}）"
            self._logger.info(msg, {
                "target": target,
                "endpoint": config.get("endpoint", ""),
            })

        worker = _UploadWorker(target, config)
        worker.signals.finished.connect(self._on_upload_finished)
        self._thread_pool.start(worker)

    @Slot(str, dict)
    def _on_upload_finished(self, target: str, result: dict) -> None:
        now_iso = datetime.now().astimezone().isoformat(timespec="milliseconds")
        success = result.get("success", False)

        # 使用縣市外掛 + 共用流程產生使用者友善訊息
        plugin = cities.get_city(target)
        if plugin:
            friendly_message = net_errors.interpret_upload_result(plugin, result)
        else:
            friendly_message = result.get("responseBody", "") or "上傳完成"

        self._city_status.setdefault(target, {}).update(
            {
                "lastUpload": now_iso,
                "lastSuccess": success,
                "lastMessage": friendly_message,
            }
        )

        if self._logger:
            log_data: dict = {"target": target}
            if success:
                self._logger.info(friendly_message, log_data)
            else:
                # 錯誤時額外記錄技術細節到 JSONL 檔案供除錯
                for key in ("endpoint", "soapAction", "statusCode",
                            "responseBody", "requestBody", "err"):
                    if key in result:
                        log_data[key] = result[key]
                self._logger.error(friendly_message, log_data)

        self.upload_completed.emit(target, success, friendly_message)

        # 更新整體狀態
        self._emit_overall_status()

    def _emit_overall_status(self) -> None:
        statuses = [s.get("lastSuccess") for s in self._city_status.values() if s.get("lastSuccess") is not None]
        if not statuses:
            self.status_changed.emit("ok")
        elif all(statuses):
            self.status_changed.emit("ok")
        elif any(statuses):
            self.status_changed.emit("warning")
        else:
            self.status_changed.emit("error")

    def _update_city_status(self) -> None:
        """初始化各城市狀態並計算下次上傳時間。"""
        if not self._schedule:
            return
        for target in cities.city_keys():
            if target not in self._city_status:
                self._city_status[target] = {}
            # 重新計算下次上傳時間
            city_config = self._schedule.get(target)
            if city_config and city_config.get("enabled"):
                interval = city_config.get("intervalMinutes", 10)
                if interval > 0:
                    next_time = self._calc_next_time(interval)
                    self._city_status[target]["nextUpload"] = next_time.isoformat()
                    self.next_upload_changed.emit(target, next_time.isoformat())

    @staticmethod
    def _calc_next_time(interval: int) -> datetime:
        """根據間隔計算下一個對齊的執行時間。"""
        now = datetime.now()
        minutes_since_midnight = now.hour * 60 + now.minute
        next_minutes = minutes_since_midnight + interval
        next_minutes -= next_minutes % interval
        if next_minutes <= minutes_since_midnight:
            next_minutes += interval
        if next_minutes >= 1440:
            return (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        return now.replace(
            hour=next_minutes // 60,
            minute=next_minutes % 60,
            second=0,
            microsecond=0,
        )
