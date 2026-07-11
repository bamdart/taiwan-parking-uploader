"""
scheduler/cities/newtaipei.py - 新北市交通局即時車位上傳外掛

服務：新北市交通局即時車位上傳 SOAP API（upRealTimeNum）
  欄位：userId, userPwd, parkingLotId, carSpace, recDate, recTime
  recDate（民國年月日）與 recTime（時分秒）於送出前由 uploader 依
  dynamicFields 動態替換 PLACEHOLDER。
成功回應：<upRealTimeNumResult>ok!...</upRealTimeNumResult>

新北市不要求定時補傳，預設關閉定時、以使用者手動「立即上傳」為主。
"""

import re

from scheduler.core import net_errors
from scheduler.core.soap import SVC_NS, wrap_envelope

from .base import CityPlugin, CredentialField, ValueField

_DEFAULT_ENDPOINT = (
    "https://www.parkinginfo.ntpc.gov.tw/ReNewParkingInfo/ReNewInfo.asmx"
)


class NewTaipeiPlugin(CityPlugin):
    key = "newTaipei"
    display_name = "新北市交通局"
    short_name = "新北市"

    endpoint_env_key = "NEWTAIPEI_ENDPOINT"
    default_endpoint = _DEFAULT_ENDPOINT

    credential_fields = [
        CredentialField(name="userId", env_key="NEWTAIPEI_USER_ID", label="使用者 ID"),
        CredentialField(
            name="userPwd", env_key="NEWTAIPEI_USER_PWD", label="密碼", secret=True
        ),
        CredentialField(
            name="parkingLotId",
            env_key="NEWTAIPEI_PARKING_LOT_ID",
            label="停車場編號",
        ),
    ]

    value_fields = [
        ValueField(key="carSpace", label="剩餘車位"),
    ]

    default_enabled = False
    default_interval = 10

    # ------------------------------------------------------------------
    # SOAP 請求格式（核心）
    # ------------------------------------------------------------------

    def build_entry(self, *, enabled, interval_minutes, values, credentials):
        car_space = values.get("carSpace", 0)
        user_id = credentials.get("userId", "")
        user_pwd = credentials.get("userPwd", "")
        parking_lot_id = credentials.get("parkingLotId", "")
        endpoint = credentials.get("endpoint", "") or self.default_endpoint

        # recDate / recTime 用 PLACEHOLDER，送出前由 uploader 依 dynamicFields 替換
        inner = (
            f'<upRealTimeNum xmlns="{SVC_NS}">'
            f"<userId>{user_id}</userId>"
            f"<userPwd>{user_pwd}</userPwd>"
            f"<parkingLotId>{parking_lot_id}</parkingLotId>"
            f"<carSpace>{car_space}</carSpace>"
            f"<recDate>PLACEHOLDER</recDate>"
            f"<recTime>PLACEHOLDER</recTime>"
            f"</upRealTimeNum>"
        )

        body_xml = wrap_envelope(inner, "soap")

        display_label = f"新北市（剩餘車位 {car_space}，場站 {parking_lot_id}）"

        return {
            "enabled": enabled,
            "intervalMinutes": interval_minutes,
            "values": {
                "carSpace": car_space,
            },
            "endpoint": endpoint,
            "soapAction": f"{SVC_NS}upRealTimeNum",
            "contentType": "text/xml; charset=utf-8",
            "body": body_xml,
            "successPattern": "OK|1|true",
            "displayLabel": display_label,
            "dynamicFields": {
                "recDate": "rocDate",
                "recTime": "hhmmss",
            },
        }

    # ------------------------------------------------------------------
    # 回應 body 解析
    # ------------------------------------------------------------------

    def interpret_body(self, body: str) -> str:
        if not body:
            return "新北市伺服器未回傳內容"

        match = re.search(
            r"<upRealTimeNumResult[^>]*>([^<]*)</upRealTimeNumResult>",
            body,
            re.IGNORECASE,
        )
        if match:
            result = match.group(1).strip()
            if result.lower().startswith("ok"):
                return "新北市上傳成功"
            # 以常見關鍵字判斷
            return _translate_error(result)

        if net_errors.has_soap_fault(body):
            return f"新北市伺服器錯誤（SOAP Fault）：{net_errors.extract_soap_fault(body)}"

        return f"新北市回應格式異常：{body[:100]}"


def _translate_error(msg: str) -> str:
    """新北市錯誤訊息關鍵字翻譯。"""
    low = msg.lower()
    if "password" in low or "pwd" in low or "密碼" in msg:
        return f"新北市上傳失敗：密碼錯誤（{msg}）"
    if "user" in low or "account" in low or "帳" in msg:
        return f"新北市上傳失敗：帳號錯誤（{msg}）"
    if "permission" in low or "denied" in low or "權限" in msg or "unauthorized" in low:
        return f"新北市上傳失敗：權限不足（{msg}）"
    if "parkinglot" in low or "parking" in low or "停車場" in msg:
        return f"新北市上傳失敗：停車場編號錯誤（{msg}）"
    if "date" in low or "time" in low or "日期" in msg or "時間" in msg:
        return f"新北市上傳失敗：日期或時間格式錯誤（{msg}）"
    if "format" in low or "invalid" in low or "格式" in msg:
        return f"新北市上傳失敗：資料格式錯誤（{msg}）"
    return f"新北市上傳失敗：{msg}"
