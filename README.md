# taiwan-parking-uploader

> 臺灣停車即時車位資料上傳排程器 — by HITech 海姆達爾智慧科技

---

## English summary

**taiwan-parking-uploader** is a small, self-contained desktop tool (Python +
PySide6) that periodically uploads a parking lot's real-time available-space
count to Taiwan's municipal parking authority APIs (SOAP). It ships a simple GUI
with a first-run setup wizard, runs from the system tray, and can auto-start on
Windows boot.

It is **fully offline-first and auditable**: the only network call it ever makes
is the SOAP `POST` to the government endpoint *you* configure. No telemetry, no
analytics, no third-party calls. Credentials live only in a local `.env`. See
[SECURITY.md](SECURITY.md).

Each supported city is a **single, self-contained plugin file** under
`scheduler/cities/`. To support your own city, copy one file and register it —
see [docs/ADD_A_CITY.md](docs/ADD_A_CITY.md). Licensed under Apache-2.0.

---

## 這是什麼

一支輕量、可獨立建置的桌面小工具，定時（或手動）把停車場的「即時剩餘車位數」上傳到
**臺灣各縣市停車主管機關的官方 API**。特色：

- 圖形介面 + 首次設定精靈，非工程師也能上手
- 常駐系統匣、可設定開機自動啟動（Windows）
- JSONL 執行紀錄，逾期自動清除
- **每個縣市一個檔案**，想接自己縣市的人複製一個檔就能 fork
- **無遙測、無第三方連線**，帳密只留在本機 → 見 [SECURITY.md](SECURITY.md)

## 目前支援縣市

| 縣市 | 服務 | 說明 |
|------|------|------|
| 臺中市交通局 | SOAP（Report / ReportWithMotor） | 支援汽車 + 機車位，官方要求每 10 分鐘補傳 |
| 新北市交通局 | SOAP（upRealTimeNum） | 手動上傳為主，送出時自動帶入民國日期/時間 |
| 臺北市停車管理工程處 | JSON（ParkingLotRemain，header 帶 APIKey） | 官方要求每分鐘上傳，支援汽車、機車、大型重機、大客車、身障優先、婦幼優先剩餘位，沒有該車種留空即可 |

> 想新增縣市？見 [docs/ADD_A_CITY.md](docs/ADD_A_CITY.md)。

## 環境需求

- Python 3.10+
- Windows（開機自動啟動與打包 exe 為 Windows 專屬；核心上傳邏輯跨平台）

## 快速開始（原始碼執行）

```bash
pip install -r requirements.txt
python main.py
```

首次啟動會出現設定精靈，選擇縣市並填入主管機關提供的 API 帳密即可。
（也可先手動複製 `.env.example` 為 `.env` 再填。）

## 打包成執行檔（Windows）

打包成單一 `.exe`，使用者不需安裝 Python 即可執行。

```bat
REM 1. 安裝相依套件（含 PyInstaller）
pip install -r requirements.txt

REM 2. 執行打包腳本
build.bat
```

`build.bat` 會以 PyInstaller onefile 模式打包，並自動偵測、內嵌 VC++/UCRT
runtime DLL（目標電腦免安裝 Visual C++ Redistributable）。完成後產物為：

```
dist-pyinstaller\臺灣停車資料上傳系統-<版本>.exe
```

此 `.exe` 為單一自帶檔，可直接複製到其他電腦執行；首次啟動會跳出設定精靈，
不需另外附任何設定檔。檔名與版本的單一來源都是
[`scheduler/branding.py`](scheduler/branding.py)：`RELEASE_NAME`（發佈檔名）與
`APP_VERSION`（版本）。

> 打包時 PyInstaller 內部先以 ASCII 名稱編譯，最後才由 Python 改成上述中文發佈檔名，
> 以避免中文路徑造成的相容性問題。

## 發佈 Release

建議流程（每次發版）：

1. 更新版本號：改 [`scheduler/branding.py`](scheduler/branding.py) 的 `APP_VERSION`。
2. 打包：執行 `build.bat`，取得 `dist-pyinstaller\臺灣停車資料上傳系統-<版本>.exe`。
3. 上 GitHub Release（用 [gh CLI](https://cli.github.com/) 最快）：

   ```bash
   gh release create v1.1.0 \
     "dist-pyinstaller/臺灣停車資料上傳系統-1.1.1.exe" \
     --title "v1.1.1" \
     --notes "更新內容..."
   ```

   或在 GitHub 網頁 **Releases → Draft a new release**，tag 填 `v1.1.1`，
   把 `.exe` 拖到附件區即可。

使用者到 Releases 頁下載那一個 `.exe`、直接執行就能用。

## 專案結構

```
main.py                   入口
scheduler/
├── branding.py           品牌與版本常數
├── main.py               應用主流程
├── core/                 排程引擎、上傳、設定、log、共用 utils
├── cities/               ★ 每縣市一個外掛檔（SOAP 格式）
└── gui/                  PySide6 介面
docs/                     架構、新增縣市指南、逐檔說明
```

詳見 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 與
[docs/FILE_REFERENCE.md](docs/FILE_REFERENCE.md)。

## 關於 HITech 海姆達爾智慧科技

HITech 海姆達爾智慧科技專注於 **AI 影像辨識**，提供車輛與車牌辨識、智慧交通執法、
智慧停車管理、人臉與行為分析、智慧零售等解決方案。此工具是我們停車解決方案的一部分，
以開源形式釋出，方便各停車場營運者與縣市使用，也讓程式碼可被公開審閱。

- 官網：<https://www.hitech.com.tw/zh/>
- Email：mainbody@hi-tech.com.tw

## 授權

Apache License 2.0 — 見 [LICENSE](LICENSE) 與 [NOTICE](NOTICE)。

&copy; 2026 Heimdall Intelligent Technology Co., Ltd.（HITech 海姆達爾智慧科技）
