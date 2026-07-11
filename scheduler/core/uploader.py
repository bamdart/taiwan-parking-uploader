"""
core/uploader.py - HTTP POST 上傳模組

讀取 schedule.json 中的完整 HTTP 請求參數（endpoint, soapAction, contentType, body），
處理 dynamicFields 動態替換後直接 POST。不負責組裝 XML。
"""

import re
from datetime import datetime

import requests

# dynamicFields 支援的替換格式
_DYNAMIC_FORMATS = {
    "rocDate": lambda now: f"{now.year - 1911:03d}{now.month:02d}{now.day:02d}",
    "hhmmss": lambda now: f"{now.hour:02d}{now.minute:02d}{now.second:02d}",
}

_REQUEST_TIMEOUT = 30


def _apply_dynamic_fields(body: str, dynamic_fields: dict) -> str:
    """替換 body 中 <tag>...</tag> 的值。

    dynamic_fields 格式：{"recDate": "rocDate", "recTime": "hhmmss"}
    會將 <recDate>...</recDate> 替換為民國年月日，<recTime>...</recTime> 替換為時分秒。
    """
    now = datetime.now()
    for tag, fmt_key in dynamic_fields.items():
        fmt_func = _DYNAMIC_FORMATS.get(fmt_key)
        if not fmt_func:
            continue
        value = fmt_func(now)
        # 替換 <tag>任意內容</tag> → <tag>新值</tag>
        pattern = rf"(<{re.escape(tag)}>)([\s\S]*?)(</{re.escape(tag)}>)"
        body = re.sub(pattern, rf"\g<1>{value}\g<3>", body)
    return body


def upload(config: dict) -> dict:
    """執行單次上傳。

    config 需包含：endpoint, soapAction, contentType, body, successPattern
    可選：dynamicFields

    回傳 {"success": bool, "message": str}
    """
    endpoint = config.get("endpoint", "")
    soap_action = config.get("soapAction", "")
    content_type = config.get("contentType", "text/xml; charset=utf-8")
    body = config.get("body", "")
    success_pattern = config.get("successPattern", "true")
    display_label = config.get("displayLabel", "")

    if not endpoint or not body:
        return {
            "success": False,
            "displayLabel": display_label,
            "endpoint": endpoint,
            "err": "endpoint 或 body 未設定",
        }

    # 動態欄位替換
    dynamic_fields = config.get("dynamicFields")
    if dynamic_fields:
        body = _apply_dynamic_fields(body, dynamic_fields)

    headers = {"Content-Type": content_type}
    if soap_action:
        headers["SOAPAction"] = soap_action

    # 基礎 log data（不含 response）
    base_data = {
        "endpoint": endpoint,
        "soapAction": soap_action,
        "requestBody": body[:500],
    }

    try:
        res = requests.post(
            endpoint,
            headers=headers,
            data=body.encode("utf-8"),
            timeout=_REQUEST_TIMEOUT,
        )

        response_text = res.text[:500]

        # 以 successPattern regex 比對回應 body（若 HTTP 失敗則標記為失敗）
        is_ok = res.ok and bool(re.search(success_pattern, res.text, re.IGNORECASE))

        return {
            "success": is_ok,
            "displayLabel": display_label,
            **base_data,
            "statusCode": res.status_code,
            "responseBody": response_text,
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "displayLabel": display_label,
            **base_data,
            "err": str(e),
        }
