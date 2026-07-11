"""
scheduler/main.py - 臺灣停車資料排程上傳器入口

PySide6 GUI 應用程式，讀取 schedule.json 定時 POST 上傳車位資料。
支援最小化到系統匣、自動偵測設定變更、JSONL log。
透過 lock file 確保只有一個實例在運行。

首次啟動（無 .env）時顯示設定精靈，引導使用者選擇縣市與輸入帳密。

縣市邏輯全數來自 scheduler.cities 註冊表，本檔不 import 特定縣市。
"""

import atexit
import os
import sys
import traceback
from datetime import datetime


def _crash_log_path() -> str:
    """取得 crash log 路徑（logs/ 子目錄，與其他執行時檔案集中）。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # scheduler/main.py → scheduler/ → 專案根目錄
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "logs", "scheduler-crash.log")


def _write_crash_log(exc: BaseException) -> None:
    """將未捕捉的例外寫入 crash log（忽略正常退出）。"""
    if isinstance(exc, SystemExit):
        return  # 正常退出不記錄
    try:
        path = _crash_log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = datetime.now().astimezone().isoformat(timespec="seconds")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n===== {ts} =====\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except OSError:
        pass


# 全域例外 hook：GUI 程式 stderr 被隱藏，任何未捕捉例外都寫入 crash log
def _excepthook(exc_type, exc_value, exc_tb):
    _write_crash_log(exc_value)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook


from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from scheduler import cities
from scheduler.core import autostart
from scheduler.core.config import ConfigManager
from scheduler.core.logger import LogManager
from scheduler.core.scheduler import SchedulerEngine
from scheduler.gui.brand import apply_brand_style, resolve_theme
from scheduler.gui.main_window import MainWindow


# ------------------------------------------------------------------
# Single instance lock（純 OS 級 file lock）
# ------------------------------------------------------------------

_lock_fd = None


def _acquire_lock(base_dir: str) -> bool:
    """嘗試取得 OS 級排他鎖。回傳 True 表示成功（無其他實例）。"""
    global _lock_fd

    lock_path = os.path.join(base_dir, ".scheduler.lock")
    try:
        if not os.path.exists(lock_path):
            open(lock_path, "wb").close()
        _lock_fd = open(lock_path, "r+b")

        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        return True
    except (OSError, IOError):
        if _lock_fd:
            _lock_fd.close()
            _lock_fd = None
        return False


def _release_lock() -> None:
    """釋放鎖並關閉 file handle。"""
    global _lock_fd

    if _lock_fd:
        try:
            if sys.platform == "win32":
                import msvcrt
                try:
                    _lock_fd.seek(0)
                    msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            _lock_fd.close()
        except OSError:
            pass
        _lock_fd = None


# ------------------------------------------------------------------
# Config save handler
# ------------------------------------------------------------------

def _on_config_save(
    config: ConfigManager, logger: LogManager, city_key: str, values: dict
) -> None:
    """從 GUI 卡片儲存排程設定：組裝 SOAP entry 後寫入 schedule.json。"""
    plugin = cities.get_city(city_key)
    if not plugin:
        return

    schedule = config.schedule or {}
    schedule[city_key] = plugin.build_entry(
        enabled=values.get("enabled", plugin.default_enabled),
        interval_minutes=values.get("intervalMinutes", plugin.default_interval),
        values=values.get("values", {}),
        credentials=config.credentials(city_key),
    )

    config.save_schedule(schedule)

    city = plugin.short_name
    enabled_txt = "開啟" if values.get("enabled") else "關閉"
    interval = values.get("intervalMinutes", 10)
    logger.info(
        f"已儲存 {city} 排程設定（定時執行：{enabled_txt}，間隔：{interval} 分鐘）",
        {
            "target": city_key,
            "enabled": values.get("enabled"),
            "intervalMinutes": interval,
            "values": values.get("values"),
        },
    )


# ------------------------------------------------------------------
# Reset handler
# ------------------------------------------------------------------

def _on_reset(config: ConfigManager, window: MainWindow, engine: SchedulerEngine, logger: LogManager) -> None:
    """清除資料並重新設定：刪除 .env、.env.local 和 schedule.json 後立即重啟。

    重啟後新程序會偵測到 needs_setup() 為 True 並自動顯示 setup wizard。
    """
    engine.stop()

    # 刪除所有設定檔（含 .env.local 避免殘留的 ACTIVE_CITY 覆蓋 .env）
    paths_to_delete = [
        config.env_path,
        os.path.join(config.base_dir, ".env.local"),
        config.schedule_path,
    ]
    for path in paths_to_delete:
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    logger.info("已清除資料，即將重新啟動程式")
    # 立即重啟，新程序會自動進入 setup wizard
    window._restart_app()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 關閉視窗不退出，由 tray 控制

    # 設定管理（需先初始化以取得 base_dir）
    config = ConfigManager()

    # 套用品牌樣式（依 .env FONT_SIZE / THEME 設定）
    theme_key = resolve_theme(app, config.theme)
    apply_brand_style(app, config.font_size, theme_key)

    # Single instance 檢查（lock 檔放 logs/ 與其他執行時檔案集中）
    if not _acquire_lock(config.data_dir):
        QMessageBox.warning(
            None,
            "程式已在運行",
            "上傳系統已經在運行中。\n請檢查系統匣圖示，或先關閉現有的程式再重新啟動。",
        )
        sys.exit(0)

    atexit.register(_release_lock)

    # 首次設定檢查
    if config.needs_setup():
        from scheduler.gui.setup_wizard import SetupWizard

        wizard = SetupWizard(config)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            _release_lock()
            sys.exit(0)
        # 重載 env 與 schedule
        config.reload_env()
        config.load()

    # 自動啟動同步：清除舊版 .vbs、修正失效的 .lnk 指向
    autostart.sync()

    # Log 管理
    logger = LogManager(config.base_dir, config.get_log_retention_days())

    # 排程引擎（傳入 config_manager，每分鐘 tick 自動重讀 schedule.json）
    engine = SchedulerEngine(config_manager=config, logger=logger)

    # GUI
    visible_cities = config.visible_cities()
    logger.info(
        f"啟動中：ACTIVE_CITY={config.active_city}，顯示 {visible_cities}"
    )

    def on_quit() -> None:
        engine.stop()
        logger.info("程式已停止")
        _release_lock()
        app.quit()

    window = MainWindow(visible_cities, on_quit, config.base_dir, config_manager=config)

    # 連接 signals —— 上傳結果
    engine.upload_completed.connect(
        lambda target, success, message: (
            window.status_panel.update_city_status(
                target, engine.get_city_status(target)
            ),
        )
    )
    engine.next_upload_changed.connect(
        lambda target, next_time: window.status_panel.update_city_status(
            target, engine.get_city_status(target)
        )
    )
    engine.status_changed.connect(window.tray.update_tooltip)
    logger.log_entry_added.connect(window.log_viewer.append_entry)

    # 排程引擎偵測到設定變更時更新 GUI
    engine.config_reloaded.connect(
        lambda schedule: (
            window.status_panel.update_config(schedule),
            window.set_status_text("排程運行中 | schedule.json: 已自動重載"),
            logger.set_retention_days(config.get_log_retention_days()),
        )
    )

    # 連接 signals —— 儲存排程
    def _on_save(city_key: str, values: dict) -> None:
        _on_config_save(config, logger, city_key, values)
        # 首次儲存時啟動 engine（之前因無 schedule.json 而未啟動）
        if not engine.is_started():
            config.load()
            if config.schedule:
                logger.info("排程已啟動")
                engine.start(config.schedule)

    window.status_panel.config_save_requested.connect(_on_save)

    # 連接 signals —— 立即上傳（儲存 → 重載 engine → 上傳）
    def _on_upload_now(city_key: str, values: dict) -> None:
        _on_config_save(config, logger, city_key, values)
        # 強制重載讓 engine 讀到剛寫入的 schedule
        config.load()
        schedule_now = config.schedule
        if schedule_now:
            engine._schedule = schedule_now
        # 若 engine 未啟動（首次），一併啟動
        if not engine.is_started() and schedule_now:
            engine.start(schedule_now)
        engine.upload_now(city_key)

    window.status_panel.upload_now_requested.connect(_on_upload_now)

    # 連接 signals —— 清除重設
    window.reset_requested.connect(
        lambda: _on_reset(config, window, engine, logger)
    )

    # 啟動：只有 schedule.json 存在時才自動啟動 engine
    # 首次使用（無 schedule.json）不自動上傳，等使用者填完車位數並按「儲存設定」才啟動
    schedule = config.schedule
    if schedule:
        window.status_panel.update_config(schedule)
        # 若只顯示單一縣市且該縣市預設不定時（手動上傳為主），顯示對應提示
        only_plugin = (
            cities.get_city(visible_cities[0]) if len(visible_cities) == 1 else None
        )
        if only_plugin is not None and not only_plugin.default_enabled:
            logger.info("已載入既有設定，請設定車位數後點擊「立即上傳」按鈕")
        else:
            logger.info("排程已啟動，將在下一個對齊時間自動上傳")
        engine.start(schedule)
    else:
        logger.info("請設定車位數與間隔後點擊「儲存設定」以啟動排程")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # 正常退出（sys.exit(0) / app.exec() 返回），不彈警告
        raise
    except BaseException as exc:
        _write_crash_log(exc)
        # 嘗試彈出錯誤對話框（若 QApplication 還活著）
        try:
            from PySide6.QtWidgets import QApplication as _QA, QMessageBox as _MB

            _app = _QA.instance() or _QA(sys.argv)
            _MB.critical(
                None,
                "啟動失敗",
                f"{exc}\n\n詳細資訊已寫入 scheduler-crash.log",
            )
        except BaseException:
            pass
        raise
