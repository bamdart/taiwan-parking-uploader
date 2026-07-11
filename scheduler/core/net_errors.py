"""
core/net_errors.py - 上傳結果的共用錯誤翻譯

把技術性錯誤轉成一般使用者能看懂的中文訊息。此模組只處理與縣市無關的
「共用層」：

  - 網路層錯誤（timeout / SSL / connection / DNS）
  - HTTP 狀態碼錯誤（401 / 403 / 404 / 5xx …）
  - SOAP Fault 擷取
  - 上傳結果的通用判讀流程 interpret_upload_result()

各縣市服務「回應 body」的專屬解析，交由該縣市外掛的 interpret_body() 處理
（見 scheduler/cities/*.py）。此模組不 import Qt，可獨立測試。

HTTP 層級錯誤對照：
  403     → IP 白名單未開通
  401     → 身份驗證失敗
  5xx     → 對方伺服器異常
  timeout → IP 未開白名單或網路不通
  SSL/TLS → 憑證或網路阻擋
"""

import re


def interpret_network_error(err: str) -> str:
    """網路層級錯誤（connection refused, timeout, ssl, dns）。"""
    if not err:
        return "網路連線失敗"
    err_l = err.lower()
    if "timeout" in err_l or "timed out" in err_l:
        return "連線逾時：伺服器無回應，可能是 IP 未加入白名單，請聯絡主管機關確認"
    if "ssl" in err_l or "certificate" in err_l or "tls" in err_l:
        return "安全連線失敗：可能是 HTTPS 憑證異常、公司網路阻擋或 TLS 版本不支援"
    if "connectionerror" in err_l or "connection refused" in err_l:
        return "無法連接伺服器：請確認網路正常且對方服務運作中"
    if "nameresolution" in err_l or "getaddrinfo" in err_l or "dns" in err_l:
        return "網址解析失敗：請檢查網路連線或 DNS 設定"
    return f"網路錯誤：{err}"


def interpret_http_status(status_code: int) -> str | None:
    """HTTP 狀態碼錯誤。回傳 None 表示非錯誤（200 系列）。"""
    if 200 <= status_code < 300:
        return None
    if status_code == 401:
        return "身份驗證失敗（HTTP 401）：帳號密碼錯誤，請透過「設定 → 開啟設定檔 (.env)」檢查"
    if status_code == 403:
        return "權限被拒（HTTP 403）：IP 未加入白名單，請聯絡主管機關開通"
    if status_code == 404:
        return "找不到服務（HTTP 404）：API 端點可能已變更，請聯絡主管機關確認"
    if status_code == 408:
        return "連線逾時（HTTP 408）：對方伺服器回應太慢，請稍後再試"
    if 500 <= status_code < 600:
        return f"對方伺服器異常（HTTP {status_code}）：可能維護中，請稍後再試"
    return f"HTTP 錯誤（{status_code}）：請聯絡主管機關"


def extract_soap_fault(body: str) -> str:
    """從 SOAP Fault 擷取錯誤描述。"""
    match = re.search(r"<faultstring[^>]*>([^<]+)</faultstring>", body, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return body[:200]


def has_soap_fault(body: str) -> bool:
    """判斷回應 body 是否為 SOAP Fault。"""
    return "<s:Fault" in body or "<soap:Fault" in body or "Fault>" in body


def interpret_success(short_name: str, display_label: str = "") -> str:
    """通用成功訊息。short_name 為縣市短名（如「臺中市」）。"""
    if display_label:
        return f"{short_name}上傳成功（{display_label}）"
    return f"{short_name}上傳成功"


def interpret_upload_result(plugin, result: dict) -> str:
    """通用上傳結果判讀流程。

    依序判斷：成功 → 網路錯誤 → HTTP 狀態碼錯誤 → 交給縣市外掛解析回應 body。

    plugin 需提供 short_name 屬性與 interpret_body(body) 方法。
    result 為 uploader.upload() 的回傳 dict，可能包含：
      - success: bool
      - statusCode: int（可能缺）
      - responseBody: str（可能缺）
      - err: str（例外時才有）
      - displayLabel: str（可能缺）
    """
    success = result.get("success", False)
    display_label = result.get("displayLabel", "")

    if success:
        return interpret_success(plugin.short_name, display_label)

    # 網路層級錯誤
    err = result.get("err")
    if err:
        return interpret_network_error(err)

    # HTTP 狀態碼錯誤
    status_code = result.get("statusCode")
    if status_code is not None:
        http_msg = interpret_http_status(int(status_code))
        if http_msg:
            return http_msg

    # 服務層級錯誤：交給縣市外掛解析
    body = result.get("responseBody", "")
    return plugin.interpret_body(body)
