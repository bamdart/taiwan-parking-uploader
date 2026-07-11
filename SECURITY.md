# 資安說明 / Security

> 本工具開源的目的之一，就是讓任何人都能自行審閱程式碼、確認它不會做設定以外的事。
> 以下說明工具的對外行為、資料儲存方式，以及如何自行驗證。

## 這個工具會做什麼

讀取本機的車位數與帳密設定，依排程（或手動觸發）把「即時剩餘車位數」以 SOAP
POST 上傳到**各縣市主管機關的官方 API**。除此之外不做任何事。

## 對外連線（唯一）

程式**只會**連線到 `schedule.json` 中設定的 endpoint，而該 endpoint 來自你自己的
`.env`（首次設定精靈填入）。預設值為各縣市官方網域：

| 縣市   | 預設 Endpoint                             |
| ------ | ----------------------------------------- |
| 臺中市 | `https://tcgis.taichung.gov.tw/...`       |
| 新北市 | `https://www.parkinginfo.ntpc.gov.tw/...` |

- **沒有任何 analytics、telemetry、遙測、回報或「呼叫母船」的行為。**
- 全專案唯一發出 HTTP 請求的程式碼在 [`scheduler/core/uploader.py`](scheduler/core/uploader.py)
  （使用 `requests.post`）。你可以用一行指令確認：

  ```bash
  grep -rn "requests\.\|urllib\|http" scheduler/
  ```

  除了 `uploader.py` 內對「你設定的 endpoint」的那一次 POST，不會有其他網路呼叫。

## 資料儲存（全部留在本機）

| 資料           | 位置                             | 說明                                |
| -------------- | -------------------------------- | ----------------------------------- |
| API 帳密       | `.env`（本機專案根）             | 已列入 `.gitignore`，不會進版本控制 |
| 排程與車位設定 | `logs/schedule.json`（本機）     |                                     |
| 執行紀錄       | `logs/scheduler-*.jsonl`（本機） | JSONL 格式，逾期自動清除            |

> 所有執行時產生的檔案（`schedule.json`、log、`.scheduler.lock`、crash log）都集中在
> `logs/` 資料夾，整個資料夾已列入 `.gitignore`。

帳密只用於組裝要送給官方 API 的 SOAP 內容，不會傳送到任何第三方。

## 系統整合行為

- **開機自動啟動**（選用，Windows）：在使用者勾選時，於 Windows「啟動」資料夾
  建立一個 `.lnk` 捷徑，指向本程式 exe。實作在
  [`scheduler/core/autostart.py`](scheduler/core/autostart.py)，透過標準的
  PowerShell `WScript.Shell` COM 物件建立捷徑，行為完全透明、可隨時取消勾選移除。
- 程式不修改登錄檔（Registry）以外的系統設定，不安裝服務，不需要管理員權限即可執行
  （系統層級開機啟動失敗時會自動降級為當前使用者層級）。

## 沒有內建機密

儲存庫中不含任何真實帳密或金鑰。`.env.example` 只是空白範本。

## 回報安全問題

若發現安全疑慮，請來信 **mainbody@hi-tech.com.tw**，請勿直接開公開 issue 揭露細節。
