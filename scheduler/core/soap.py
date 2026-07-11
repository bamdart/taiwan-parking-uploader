"""
core/soap.py - 共用 SOAP 打包 helper

各縣市外掛（scheduler/cities/*.py）import 此模組來組裝自己的 SOAP body 與
Envelope，避免每個縣市檔重抄相同的樣板。

此模組不含任何縣市專屬邏輯，也不 import Qt，可獨立測試。
"""

# SOAP 1.1 envelope namespace
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"

# .NET WCF / ASMX 服務預設的 tempuri namespace。
# 臺中市與新北市的服務皆使用此預設值；若某縣市服務使用自訂 namespace，
# 該縣市外掛可自行定義，不必沿用此常數。
SVC_NS = "http://tempuri.org/"


def wrap_envelope(body_xml: str, prefix: str = "s") -> str:
    """把 <Body> 內容包成完整 SOAP Envelope。

    prefix 為 namespace 前綴（臺中慣例用 "s"、新北慣例用 "soap"）。
    """
    return (
        f'<?xml version="1.0" encoding="utf-8"?>'
        f'<{prefix}:Envelope xmlns:{prefix}="{SOAP_NS}">'
        f'<{prefix}:Body>{body_xml}</{prefix}:Body>'
        f'</{prefix}:Envelope>'
    )
