"""
scheduler/cities/taipei.py - 臺北市停車管理工程處剩餘車位上傳外掛

服務：臺北市停車場一般車格位剩餘格位上傳 API（v1.4，整場剩餘車位數上傳）
  POST https://ParkDataRT.pma.gov.tw/api/ParkingLotRemain
  非 SOAP：JSON body，header 帶機關發給廠商的 APIKey。
  body：{"Data_real": {"UpdateTime", "ParkID", "ParkingLotRemain": [{"Type", "RemainNumber"}]}}
  UpdateTime（YYYY-MM-DD HH:MM:SS）於送出前由 uploader 依 dynamicFields 動態替換。
成功回應：{"response": {"msg": "成功", "code": "200"}}

規格書要求每分鐘上傳一次，故預設啟用定時、間隔 1 分鐘。
規格書六種車種皆有對應欄位且一律送出；沒有該車種時剩餘車位填 -9。各欄位可留空，
留空即自動送 -9（UI 不揭露 -9，使用者只需留空）。
"""

import json

from .base import CityPlugin, CredentialField, ValueField

_DEFAULT_ENDPOINT = "https://ParkDataRT.pma.gov.tw/api/ParkingLotRemain"

# 規格書：沒有該車種時剩餘車位填 -9
_NO_SUCH_TYPE = -9

# 規格書 ParkingLotRemain.Type 車種：(values key, API Type, UI 標籤)
# 順序即卡片欄位與送出順序
_REMAIN_TYPES = [
    ("carRemaining", "Car", "汽車"),
    ("motorRemaining", "Motor", "機車"),
    ("heavyMotorRemaining", "HeavyMotor", "大型重機"),
    ("busRemaining", "Bus", "大客車"),
    ("handicapRemaining", "Handicap_Priority", "身障優先"),
    ("pregnancyRemaining", "Pregnancy_Priority", "婦幼優先"),
]

# 規格書附件一 response code 定義
_RESPONSE_CODES = {
    "200": "成功",
    "300": "無使用權限",
    "400": "目前無法支援此功能",
    "500": "參數錯誤",
    "600": "查無資料",
}


class TaipeiPlugin(CityPlugin):
    key = "taipei"
    display_name = "臺北市停車管理工程處"
    short_name = "臺北市"

    endpoint_env_key = "TAIPEI_ENDPOINT"
    default_endpoint = _DEFAULT_ENDPOINT

    credential_fields = [
        CredentialField(
            name="parkId", env_key="TAIPEI_PARK_ID", label="停車場代碼（ParkID）"
        ),
        CredentialField(
            name="apiKey", env_key="TAIPEI_API_KEY", label="APIKey", secret=True
        ),
    ]

    value_fields = [
        ValueField(key=key, label=f"{label}剩餘", blank_value=_NO_SUCH_TYPE)
        for key, _type, label in _REMAIN_TYPES
    ]

    # 臺北市規格書要求每分鐘上傳一次
    default_enabled = True
    default_interval = 1

    # ------------------------------------------------------------------
    # JSON 請求格式（核心）
    # ------------------------------------------------------------------

    def build_entry(self, *, enabled, interval_minutes, values, credentials):
        remains = {
            key: values.get(key, _NO_SUCH_TYPE) for key, _type, _label in _REMAIN_TYPES
        }
        park_id = credentials.get("parkId", "")
        api_key = credentials.get("apiKey", "")
        endpoint = credentials.get("endpoint", "") or self.default_endpoint

        # UpdateTime 用 PLACEHOLDER，送出前由 uploader 依 dynamicFields 替換
        payload = {
            "Data_real": {
                "UpdateTime": "PLACEHOLDER",
                "ParkID": park_id,
                "ParkingLotRemain": [
                    {"Type": api_type, "RemainNumber": remains[key]}
                    for key, api_type, _label in _REMAIN_TYPES
                ],
            }
        }

        # 只列出有填值的車種，避免訊息過長
        filled = [
            f"{label} {remains[key]}"
            for key, _type, label in _REMAIN_TYPES
            if remains[key] != _NO_SUCH_TYPE
        ]
        display_label = f"臺北市（{'，'.join(filled) or '未填車位'}，場站 {park_id}）"

        return {
            "enabled": enabled,
            "intervalMinutes": interval_minutes,
            "values": remains,
            "endpoint": endpoint,
            "soapAction": "",
            "contentType": "application/json; charset=utf-8",
            "headers": {"APIKey": api_key},
            "body": json.dumps(payload, ensure_ascii=False),
            "successPattern": r'"code"\s*:\s*"?200\b',
            "displayLabel": display_label,
            "dynamicFields": {
                "UpdateTime": "datetime",
            },
        }

    # ------------------------------------------------------------------
    # 回應 body 解析
    # ------------------------------------------------------------------

    def interpret_body(self, body: str) -> str:
        if not body:
            return "臺北市伺服器未回傳內容"

        try:
            data = json.loads(body)
        except ValueError:
            return f"臺北市回應格式異常：{body[:100]}"

        response = data.get("response", {}) if isinstance(data, dict) else {}
        code = str(response.get("code", ""))
        msg = response.get("msg", "")

        if code == "200":
            return "臺北市上傳成功"
        if code == "300":
            return f"臺北市上傳失敗：無使用權限，請確認 APIKey 是否正確（{msg}）"
        if code == "500":
            return f"臺北市上傳失敗：參數錯誤，請確認停車場代碼與車位數（{msg}）"
        if code in _RESPONSE_CODES:
            return f"臺北市上傳失敗：{_RESPONSE_CODES[code]}（{msg}）"
        return f"臺北市回應異常：{body[:100]}"

