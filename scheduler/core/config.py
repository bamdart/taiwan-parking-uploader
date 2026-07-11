"""
core/config.py - 設定管理

讀取 schedule.json 與 .env，提供帳密存取、schedule 建構與儲存。
透過 QFileSystemWatcher 監聽 schedule.json 變更並自動重載。

本檔不含任何縣市專屬邏輯：帳密欄位、預設值、SOAP 格式一律向 scheduler.cities
註冊表查詢，因此新增縣市不需改動此檔。
"""

import json
import os

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal

from scheduler import cities


def _resolve_base_dir() -> str:
    """解析 base 目錄：編譯後的 exe 用 exe 所在目錄，開發時用專案根目錄。

    開發模式路徑：
      入口 main.py 位於專案根目錄，Python CWD 即為專案根。
      本檔 scheduler/core/config.py → 上溯 2 層即為專案根。
    """
    import sys

    if getattr(sys, "frozen", False):
        # PyInstaller onefile: sys.executable 指向 exe
        return os.path.dirname(os.path.abspath(sys.executable))
    # 開發模式：__file__ = <project>/scheduler/core/config.py
    here = os.path.dirname(os.path.abspath(__file__))  # scheduler/core/
    return os.path.dirname(os.path.dirname(here))  # scheduler/ → 專案根目錄


def _parse_env_file(env_path: str) -> dict[str, str]:
    """解析 .env 檔案，回傳 key-value dict。處理 BOM、空行、註解。"""
    if not os.path.isfile(env_path):
        return {}
    try:
        raw = open(env_path, "r", encoding="utf-8-sig").read()
    except OSError:
        return {}

    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


class ConfigManager(QObject):
    """schedule.json + .env 設定管理器。"""

    config_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_dir = _resolve_base_dir()
        # 所有執行時產生的檔案（schedule.json、log、lock、crash log）集中於 logs/，
        # 讓專案根目錄保持乾淨（只留原始碼與 .env）。
        self._data_dir = os.path.join(self._base_dir, "logs")
        os.makedirs(self._data_dir, exist_ok=True)
        self._schedule_path = os.path.join(self._data_dir, "schedule.json")
        self._env_path = os.path.join(self._base_dir, ".env")
        self._env_local_path = os.path.join(self._base_dir, ".env.local")
        self._env_example_path = os.path.join(self._base_dir, ".env.example")

        # 讀取 .env
        self._env_vars = self._load_env_vars()
        self._active_city = self._env_vars.get("ACTIVE_CITY", "ALL").strip().upper()

        # 載入設定
        self._schedule: dict | None = None
        self.load()

        # QFileSystemWatcher
        self._watcher = QFileSystemWatcher(parent=self)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(500)
        self._debounce_timer.timeout.connect(self._do_reload)
        self._setup_watcher()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_env_vars(self) -> dict[str, str]:
        """載入並合併 .env + .env.local。"""
        env_vars = _parse_env_file(self._env_path)
        env_local = _parse_env_file(self._env_local_path)
        env_vars.update(env_local)
        return env_vars

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def base_dir(self) -> str:
        return self._base_dir

    @property
    def data_dir(self) -> str:
        """執行時檔案（schedule.json、log、lock、crash log）所在目錄 = base_dir/logs。"""
        return self._data_dir

    @property
    def env_path(self) -> str:
        return self._env_path

    @property
    def schedule_path(self) -> str:
        return self._schedule_path

    @property
    def env_vars(self) -> dict[str, str]:
        """完整 .env key-value dict（合併 .env + .env.local）。"""
        return self._env_vars

    @property
    def schedule(self) -> dict | None:
        return self._schedule

    @property
    def active_city(self) -> str:
        """回傳 ACTIVE_CITY（大寫），如 'TAICHUNG', 'NEWTAIPEI', 'ALL'。"""
        return self._active_city

    @property
    def font_size(self) -> str:
        """回傳字體大小設定（standard / large / xlarge）。"""
        val = self._env_vars.get("FONT_SIZE", "standard").strip().lower()
        if val in ("standard", "large", "xlarge"):
            return val
        return "standard"

    @property
    def theme(self) -> str:
        """回傳主題設定（system / light / dark）。"""
        val = self._env_vars.get("THEME", "system").strip().lower()
        if val in ("system", "light", "dark"):
            return val
        return "system"

    def visible_cities(self) -> list[str]:
        """依 ACTIVE_CITY 回傳需顯示的城市 key 列表。

        ACTIVE_CITY = 某縣市 key（大寫，如 'TAICHUNG'）時只顯示該縣市；
        'ALL' 或無法對應時顯示全部已註冊縣市。
        """
        if self._active_city != "ALL":
            for key in cities.city_keys():
                if key.upper() == self._active_city:
                    return [key]
        return cities.city_keys()

    def get_log_retention_days(self) -> int:
        if self._schedule:
            return self._schedule.get("logRetentionDays", 90)
        return 90

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def credentials(self, city_key: str) -> dict[str, str]:
        """依縣市外掛宣告的 credential_fields，從 .env 組出帳密 dict。

        回傳 dict 的 key 為各 CredentialField.name，另含 "endpoint" 一項。
        """
        plugin = cities.get_city(city_key)
        if not plugin:
            return {}
        creds = {
            f.name: self._env_vars.get(f.env_key, "") for f in plugin.credential_fields
        }
        if plugin.endpoint_env_key:
            creds["endpoint"] = self._env_vars.get(plugin.endpoint_env_key, "")
        return creds

    def _has_credentials(self, plugin) -> bool:
        """該縣市所需的帳密欄位是否都已填（endpoint 有預設值故不算必填）。"""
        return all(self._env_vars.get(f.env_key) for f in plugin.credential_fields)

    # ------------------------------------------------------------------
    # First-run detection
    # ------------------------------------------------------------------

    def needs_setup(self) -> bool:
        """True if .env 不存在或依 ACTIVE_CITY 所需的帳密未設定。"""
        if not os.path.isfile(self._env_path):
            return True

        if self._active_city != "ALL":
            visible = self.visible_cities()
            plugin = cities.get_city(visible[0]) if visible else None
            if not plugin:
                return True
            return not self._has_credentials(plugin)

        # ALL：任一縣市帳密都沒填齊就需要 setup
        return not any(
            self._has_credentials(cities.get_city(k)) for k in cities.city_keys()
        )

    # ------------------------------------------------------------------
    # Save .env
    # ------------------------------------------------------------------

    def save_env(self, values: dict[str, str]) -> None:
        """寫入 .env。以 .env.example 為模板，填入 values 中的值。"""
        # 讀取模板
        template_lines: list[str] = []
        if os.path.isfile(self._env_example_path):
            try:
                raw = open(self._env_example_path, "r", encoding="utf-8-sig").read()
                template_lines = raw.splitlines()
            except OSError:
                pass

        if template_lines:
            # 以模板為基礎，替換有值的 key
            output_lines: list[str] = []
            written_keys: set[str] = set()
            for line in template_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, _, _ = stripped.partition("=")
                    key = key.strip()
                    if key in values:
                        output_lines.append(f"{key}={values[key]}")
                        written_keys.add(key)
                    else:
                        output_lines.append(line)
                else:
                    output_lines.append(line)

            # 寫入模板中沒有的 key
            for key, value in values.items():
                if key not in written_keys:
                    output_lines.append(f"{key}={value}")

            content = "\n".join(output_lines) + "\n"
        else:
            # 無模板，直接寫
            lines = [f"{k}={v}" for k, v in values.items()]
            content = "\n".join(lines) + "\n"

        with open(self._env_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def update_env_value(self, key: str, value: str) -> None:
        """更新 .env 中的單一 key。若 key 不存在則新增到檔尾。"""
        if not os.path.isfile(self._env_path):
            with open(self._env_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"{key}={value}\n")
            self._env_vars[key] = value
            return

        try:
            raw = open(self._env_path, "r", encoding="utf-8-sig").read()
        except OSError:
            return

        lines = raw.splitlines()
        found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, _ = stripped.partition("=")
                if k.strip() == key:
                    lines[i] = f"{key}={value}"
                    found = True
                    break
        if not found:
            lines.append(f"{key}={value}")

        with open(self._env_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")

        self._env_vars[key] = value

    # ------------------------------------------------------------------
    # Save / Build schedule
    # ------------------------------------------------------------------

    def save_schedule(self, schedule: dict) -> None:
        """寫入 schedule.json（pretty-print, UTF-8）。"""
        with open(self._schedule_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def build_schedule(self, overrides: dict | None = None) -> dict:
        """從 .env 帳密 + 現有車位值組裝完整 schedule（走各縣市外掛）。

        overrides 可覆蓋特定城市的 enabled / intervalMinutes / values。
        """
        current = self._schedule or {}
        overrides = overrides or {}

        schedule: dict = {"logRetentionDays": current.get("logRetentionDays", 90)}

        for key in self.visible_cities():
            plugin = cities.get_city(key)
            if not plugin:
                continue
            existing = current.get(key, {})
            city_overrides = overrides.get(key, {})
            vals = {
                **existing.get("values", {}),
                **city_overrides.get("values", {}),
            }
            schedule[key] = plugin.build_entry(
                enabled=city_overrides.get(
                    "enabled", existing.get("enabled", plugin.default_enabled)
                ),
                interval_minutes=city_overrides.get(
                    "intervalMinutes",
                    existing.get("intervalMinutes", plugin.default_interval),
                ),
                values=vals,
                credentials=self.credentials(key),
            )

        return schedule

    # ------------------------------------------------------------------
    # Reload env
    # ------------------------------------------------------------------

    def reload_env(self) -> None:
        """重新讀取 .env（setup wizard 完成後呼叫）。"""
        self._env_vars = self._load_env_vars()
        self._active_city = self._env_vars.get("ACTIVE_CITY", "ALL").strip().upper()

    # ------------------------------------------------------------------
    # Load / Reload schedule.json
    # ------------------------------------------------------------------

    def load(self) -> dict | None:
        if not os.path.isfile(self._schedule_path):
            self._schedule = None
            return None
        try:
            raw = open(self._schedule_path, "r", encoding="utf-8-sig").read()
            self._schedule = json.loads(raw)
            return self._schedule
        except (OSError, json.JSONDecodeError):
            self._schedule = None
            return None

    def reload(self) -> bool:
        """重新載入，回傳 True 表示內容有變更。"""
        old = json.dumps(self._schedule, sort_keys=True) if self._schedule else ""
        self.load()
        new = json.dumps(self._schedule, sort_keys=True) if self._schedule else ""
        if old != new:
            self.config_changed.emit(self._schedule or {})
            return True
        return False

    # ------------------------------------------------------------------
    # File watcher
    # ------------------------------------------------------------------

    def _setup_watcher(self) -> None:
        if os.path.isfile(self._schedule_path):
            self._watcher.addPath(self._schedule_path)
        else:
            self._watcher.addPath(os.path.dirname(self._schedule_path))
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_dir_changed)

    def _on_file_changed(self, path: str) -> None:
        # Windows QFileSystemWatcher 常在檔案替換後失去監聽，re-add
        if not self._watcher.files() or path not in self._watcher.files():
            if os.path.isfile(self._schedule_path):
                self._watcher.addPath(self._schedule_path)
        self._debounce_timer.start()

    def _on_dir_changed(self, path: str) -> None:
        # 偵測到 schedule.json 被建立
        if os.path.isfile(self._schedule_path):
            if self._schedule_path not in (self._watcher.files() or []):
                self._watcher.addPath(self._schedule_path)
            self._debounce_timer.start()

    def _do_reload(self) -> None:
        self.reload()
