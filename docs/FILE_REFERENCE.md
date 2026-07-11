# taiwan-parking-uploader 檔案參考手冊

> 最後更新：2026-07-11
> 維護指引：新增或修改檔案時，請同步更新此文件

## 根目錄

| 檔案 | 說明 |
|------|------|
| `main.py` | 應用進入點，`from scheduler.main import main` |
| `build.bat` | PyInstaller onefile 建置腳本；產出 `dist-pyinstaller\<RELEASE_NAME>-<版本>.exe`（名稱/版本取自 branding.py） |
| `requirements.txt` | Python 相依（PySide6 / requests / pyinstaller） |
| `.env.example` | 設定範本（縣市帳密、ACTIVE_CITY、FONT_SIZE、THEME） |
| `LICENSE` / `NOTICE` | Apache-2.0 授權與第三方聲明 |
| `SECURITY.md` | 資安透明度說明（對外連線、資料儲存、如何審閱） |

## scheduler/

| 檔案 | 主要內容 | 說明 |
|------|----------|------|
| `branding.py` | `APP_VERSION`, `APP_NAME`, `RELEASE_NAME`, `COMPANY_*` | 品牌、版本、發佈檔名常數的單一來源 |
| `main.py` | `main()`, `_on_config_save()` | 組裝、連接 signals，縣市邏輯全走註冊表 |

## scheduler/core/

| 檔案 | 主要類別/函數 | 說明 |
|------|--------------|------|
| `config.py` | `ConfigManager` | 讀寫 `.env`/`schedule.json`；`credentials()`/`needs_setup()`/`visible_cities()`/`build_schedule()` 皆走註冊表；監聽檔案變更 |
| `scheduler.py` | `SchedulerEngine` | 每分鐘 tick、對齊間隔、`QThreadPool` 背景上傳 |
| `uploader.py` | `upload()` | 唯一發 HTTP 的模組；處理 `dynamicFields` 後 POST |
| `soap.py` | `wrap_envelope()`, `SVC_NS` | 共用 SOAP 打包 helper（不 import Qt） |
| `net_errors.py` | `interpret_upload_result()` 等 | 網路/HTTP 錯誤翻譯 + 通用結果流程（不 import Qt） |
| `logger.py` | `LogManager` | JSONL log，含記憶體 buffer 與逾期清除 |
| `autostart.py` | `enable()`/`disable()`/`sync()` | Windows 開機自動啟動（PowerShell 建 .lnk），品牌名取自 branding.py |

## scheduler/cities/（每縣市一個檔案）

| 檔案 | 主要類別 | 說明 |
|------|----------|------|
| `__init__.py` | `REGISTRY`, `register()`, `get_city()`, `all_cities()`, `city_keys()` | 縣市註冊表 |
| `base.py` | `CityPlugin`, `CredentialField`, `ValueField` | 外掛介面與欄位宣告型別（不 import Qt） |
| `taichung.py` | `TaichungPlugin` | 臺中市：Report / ReportWithMotor（含機車位） |
| `newtaipei.py` | `NewTaipeiPlugin` | 新北市：upRealTimeNum（含動態日期/時間欄位） |

> 新增縣市見 `ADD_A_CITY.md`。

## scheduler/gui/

| 檔案 | 主要類別 | 說明 |
|------|----------|------|
| `main_window.py` | `MainWindow` | 主視窗：卡片 + log + 公司資訊列 + 選單/狀態列 |
| `setup_wizard.py` | `SetupWizard` | 首次設定精靈；縣市與帳密欄位由註冊表動態生成 |
| `status_panel.py` | `StatusPanel`, `EditableCityCard` | 城市卡片；車位欄位由 `plugin.value_fields` 生成 |
| `log_viewer.py` | `LogViewer` | 即時 JSONL log 顯示 |
| `tray_icon.py` | `TrayIcon` | 系統匣圖示與選單 |
| `brand.py` | QSS、主題、字級 | HITech 品牌設計 QSS（明亮/黑暗、三種字級） |
| `_favicon.py` | `favicon_qicon()` | 內嵌 base64 ICO 圖示 |
| `resources/favicon.ico` | — | 應用程式圖示原始檔 |
