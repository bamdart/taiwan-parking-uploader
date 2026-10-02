# taiwan-parking-uploader 系統架構文件

> 最後更新：2026-10-02
> 維護指引：新增或修改模組時，請同步更新此文件與 `FILE_REFERENCE.md`

## 1. 專案概述

PySide6 桌面 GUI 應用程式，定時（或手動）把停車場即時剩餘車位數以 SOAP POST
上傳到各縣市主管機關官方 API。設計核心是**縣市外掛化**：每個縣市封裝成一個檔案，
排程引擎、設定管理與 GUI 完全與縣市無關。

| 運行模式 | 入口 | 說明 |
|----------|------|------|
| 開發 | `python main.py` | CWD 即專案根，讀根目錄 `.env`、`logs/schedule.json` |
| 發佈 | `scheduler-<版本>.exe` | PyInstaller onefile，讀 exe 同目錄設定檔 |

## 2. 系統架構圖

```
                            main.py
                             │
                       scheduler/main.py ── 組裝、連接 signals
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                     │
   core/config.py      core/scheduler.py       gui/*.py
   （.env/schedule）    （QTimer 排程）        （視窗/卡片/精靈/匣）
        │                    │                     │
        │              core/uploader.py            │
        │              （requests.post）            │
        └──────────► scheduler/cities ◄────────────┘
                   （每縣市外掛：SOAP 格式）
                             │
                 core/soap.py / core/net_errors.py
                     （共用 SOAP / 錯誤翻譯）
```

## 3. 核心流程

1. `main()` 建 `ConfigManager` → 套用品牌樣式 → 取單一實例鎖。
2. 若 `needs_setup()`（無 `.env` 或帳密未填）→ 顯示 `SetupWizard`，寫入 `.env`。
3. 建 `LogManager`、`SchedulerEngine`、`MainWindow`，連接 signals。
4. `SchedulerEngine` 每分鐘 `:00` tick：重讀 `schedule.json`，對每個 `enabled` 且
   到達間隔對齊時間的縣市，用 `QThreadPool` 背景 `upload()`。
5. 上傳結果經 `net_errors.interpret_upload_result(plugin, result)` 轉成友善訊息，
   更新卡片與 JSONL log。

## 4. 縣市外掛機制（重點）

- 註冊表：`scheduler/cities/__init__.py`（`REGISTRY` / `register` / `get_city` /
  `all_cities` / `city_keys`）。
- 介面：`scheduler/cities/base.py` 的 `CityPlugin` + `CredentialField` + `ValueField`。
- 每縣市檔（如 `taichung.py`）宣告欄位、實作 `build_entry`（SOAP 或 JSON 請求格式）與
  `interpret_body`（回應解析）。
- **與縣市無關的層一律走註冊表**：
  - `config.credentials/needs_setup/visible_cities/build_schedule`
  - `scheduler` 的 tick 迴圈
  - `gui/setup_wizard`（動態生成 radio + 帳密表單）
  - `gui/status_panel`（動態生成車位輸入欄）

新增縣市不需改上述任何檔，詳見 `ADD_A_CITY.md`。

## 5. 模組依賴層級

```
Layer 0  branding.py（無相依）
Layer 1  core/soap.py, core/net_errors.py（純函式，不 import Qt）
Layer 2  cities/*（import Layer 0/1；不 import Qt）
Layer 3  core/config.py, core/scheduler.py, core/uploader.py,
         core/logger.py, core/autostart.py（import cities + Qt）
Layer 4  gui/*（import Layer 0–3 + Qt）
Layer 5  main.py（組裝全部）
```

> 禁止反向依賴：`cities/*` 與 `core/soap.py`、`core/net_errors.py` 不得 import Qt 或 GUI。

## 6. 設定與資料檔

`.env` 位於專案根（exe 同目錄）；**所有執行時產生的檔案集中於 `logs/` 子目錄**，
讓根目錄保持乾淨。`logs/` 由 `ConfigManager` 啟動時自動建立。

| 檔案 | 位置 | 用途 |
|------|------|------|
| `.env` | 專案根 | 縣市帳密、`ACTIVE_CITY`、`FONT_SIZE`、`THEME`（gitignored） |
| `schedule.json` | `logs/` | 各縣市完整上傳設定（含 SOAP body），排程器直接 POST |
| `scheduler-YYYY-MM-DD.jsonl` | `logs/` | 每日一檔 JSONL log，逾 `logRetentionDays` 自動清除 |
| `scheduler-crash.log` | `logs/` | 未捕捉例外的堆疊記錄 |
| `.scheduler.lock` | `logs/` | 單一實例 OS 級鎖 |

## 7. 建置與部署

- `build.bat`：PyInstaller onefile；自動偵測並打包 VC++ / UCRT runtime DLL；
  內部以 ASCII 名稱編譯後，由 Python 依 `branding.RELEASE_NAME` + `APP_VERSION`
  改成英文發佈檔名；產物於 `dist-pyinstaller/<RELEASE_NAME>-<版本>.exe`
  （即 `taiwan-parking-uploader-<版本>.exe`）。
- 發佈流程見 README「發佈 Release」：更新 `APP_VERSION` → `build.bat` → GitHub Release。

## 8. 環境需求

- Python 3.10+、PySide6 6.7+、requests 2.31+
- 開機自動啟動與 exe 打包為 Windows 專屬功能。
