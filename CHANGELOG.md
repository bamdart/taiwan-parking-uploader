# Changelog

本專案遵循 [語意化版本](https://semver.org/lang/zh-TW/)。
版本號的單一來源是 `scheduler/branding.py` 的 `APP_VERSION`。

## [Unreleased]

### 新增
- 支援臺北市停車管理工程處剩餘車位上傳（ParkingLotRemain JSON API，header 帶 APIKey，
  預設每分鐘上傳；支援汽車、機車、大型重機、大客車、身障優先、婦幼優先六種剩餘位，
  留空即表示無此車種）。
- 縣市外掛可回傳 `headers` 帶額外 HTTP header；`dynamicFields` 支援 JSON body 與
  `datetime`（YYYY-MM-DD HH:MM:SS）格式；`ValueField` 新增 `blank_value`（允許留空，送出時自動帶入）。

## [1.1.0] - 2026-07-11

首次公開版本。

### 新增
- 各縣市即時剩餘車位定時／手動 SOAP 上傳。
- 支援縣市：臺中市交通局（Report / ReportWithMotor，含機車位）、
  新北市交通局（upRealTimeNum，含動態民國日期/時間欄位）。
- **每縣市一個外掛檔**的擴充架構（`scheduler/cities/`），新增縣市不需改共用程式。
- PySide6 GUI：首次設定精靈、可編輯城市卡片、系統匣常駐、Windows 開機自動啟動。
- JSONL 執行紀錄，逾期自動清除；所有執行時檔案集中於 `logs/`。
- PyInstaller onefile 打包（`build.bat`），自動內嵌 VC++/UCRT runtime DLL。
