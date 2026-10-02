# 如何新增一個縣市

> 最後更新：2026-10-02

本工具採「每縣市一個檔案」的外掛設計。新增一個縣市**只需兩步**，不必改動
`config` / `scheduler` / GUI —— 它們會自動套用你的新縣市。

## 一個縣市外掛負責什麼

一個縣市外掛（`scheduler/cities/<yourcity>.py`）就是一個 `CityPlugin` 子類別，
宣告：

- **識別**：`key`（schedule.json 用）、`display_name`（UI 全名）、`short_name`（訊息短名）
- **Endpoint**：`endpoint_env_key`、`default_endpoint`
- **帳密欄位** `credential_fields`：設定精靈依此生成輸入欄、`.env` 依此讀寫
- **車位欄位** `value_fields`：主畫面卡片依此生成數字輸入欄
- **預設排程** `default_enabled` / `default_interval`
- **`build_entry(...)`** ★核心：把帳密與車位數組成該縣市「整理後的 SOAP 請求格式」
- **`interpret_body(body)`**：解析該縣市回應，回傳友善訊息（網路/HTTP 錯誤已由共用層處理）

共用工具（不必自己重寫）：
- `scheduler/core/soap.py` — `wrap_envelope()` 幫你包 SOAP Envelope、`SVC_NS`
- `scheduler/core/net_errors.py` — SOAP Fault 擷取、網路/HTTP 錯誤翻譯

## 步驟一：複製一個範例改寫

以 [`scheduler/cities/taichung.py`](../scheduler/cities/taichung.py) 為藍本最完整。
下面是最精簡的骨架：

```python
# scheduler/cities/kaohsiung.py
import re

from scheduler.core import net_errors
from scheduler.core.soap import SVC_NS, wrap_envelope
from .base import CityPlugin, CredentialField, ValueField


class KaohsiungPlugin(CityPlugin):
    key = "kaohsiung"
    display_name = "高雄市交通局"
    short_name = "高雄市"

    endpoint_env_key = "KAOHSIUNG_ENDPOINT"
    default_endpoint = "https://example.kcg.gov.tw/ParkingService.asmx"

    credential_fields = [
        CredentialField(name="account", env_key="KAOHSIUNG_ACCOUNT", label="帳號"),
        CredentialField(name="password", env_key="KAOHSIUNG_PASSWORD",
                        label="密碼", secret=True),
    ]

    value_fields = [
        ValueField(key="remainingCount", label="剩餘車位"),
    ]

    default_enabled = True
    default_interval = 10

    def build_entry(self, *, enabled, interval_minutes, values, credentials):
        remaining = values.get("remainingCount", 0)
        account = credentials.get("account", "")
        password = credentials.get("password", "")
        endpoint = credentials.get("endpoint", "") or self.default_endpoint

        inner = (
            f'<Report xmlns="{SVC_NS}">'
            f"<Account>{account}</Account>"
            f"<Password>{password}</Password>"
            f"<Remaining>{remaining}</Remaining>"
            f"</Report>"
        )
        body_xml = wrap_envelope(inner, "s")

        return {
            "enabled": enabled,
            "intervalMinutes": interval_minutes,
            "values": {"remainingCount": remaining},
            "endpoint": endpoint,
            "soapAction": f"{SVC_NS}Report",
            "contentType": "text/xml; charset=utf-8",
            "body": body_xml,
            "successPattern": "true",           # 用來判定成功的 regex
            "displayLabel": f"高雄市（剩餘 {remaining}）",
        }

    def interpret_body(self, body: str) -> str:
        if re.search(r">\s*true\s*<", body, re.IGNORECASE):
            return "高雄市上傳成功"
        if net_errors.has_soap_fault(body):
            return f"高雄市伺服器錯誤：{net_errors.extract_soap_fault(body)}"
        return f"高雄市上傳失敗：{body[:100]}"
```

### 需要動態欄位（如民國日期/時間）？

回傳 entry 時多帶一個 `dynamicFields`，`uploader` 會在送出前替換 `body` 中對應
tag 的內容。目前支援：`rocDate`（民國年月日）、`hhmmss`（時分秒）、
`datetime`（`YYYY-MM-DD HH:MM:SS`）。範例見
[`scheduler/cities/newtaipei.py`](../scheduler/cities/newtaipei.py)：

```python
"dynamicFields": {"recDate": "rocDate", "recTime": "hhmmss"},
```

### 服務不是 SOAP（JSON + API Key header）？

`body` 直接放 JSON 字串、`contentType` 改 `application/json; charset=utf-8`、
`soapAction` 給空字串，額外 header 放在 `headers`。`dynamicFields` 對 JSON body
一樣有效（替換 `"tag": "..."` 的值）。範例見
[`scheduler/cities/taipei.py`](../scheduler/cities/taipei.py)：

```python
"soapAction": "",
"contentType": "application/json; charset=utf-8",
"headers": {"APIKey": api_key},
"body": json.dumps(payload, ensure_ascii=False),
"dynamicFields": {"UpdateTime": "datetime"},
```

車位欄位允許留空（如臺北市「無此車種」）時，`ValueField` 帶 `blank_value`：
使用者留空，送出時自動帶入該值（UI 只顯示留空，不顯示此值）。

```python
ValueField(key="motorRemaining", label="機車剩餘", blank_value=-9),
```

## 步驟二：註冊

在 [`scheduler/cities/__init__.py`](../scheduler/cities/__init__.py) import 並註冊一行：

```python
from .kaohsiung import KaohsiungPlugin
...
register(KaohsiungPlugin())
```

完成。啟動程式後，設定精靈會出現「高雄市交通局」選項，主畫面會有對應卡片，
`.env` 會使用你宣告的 `KAOHSIUNG_*` key。

## 只想給自己的縣市用（精簡 fork）

只保留你自己的縣市檔、在 `__init__.py` 只 `register()` 你的縣市即可；其餘縣市檔可刪。
`ACTIVE_CITY` 設成你的縣市 key，介面就只顯示你的縣市。

## 測試你的外掛（免 GUI）

縣市外掛不依賴 Qt，可直接在 Python 測：

```python
from scheduler.cities.kaohsiung import KaohsiungPlugin
p = KaohsiungPlugin()
entry = p.build_entry(enabled=True, interval_minutes=10,
                      values={"remainingCount": 5},
                      credentials={"account": "a", "password": "b", "endpoint": ""})
print(entry["body"])          # 檢查 SOAP 格式
print(p.interpret_body("<x>true</x>"))
```
