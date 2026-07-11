"""
scheduler/cities/taichung.py - 臺中市交通局停車即時車位上傳外掛

服務：臺中市停車管理處 SOAP Web Service
  - 無機車位：呼叫 Report（Account, Password, TotalCount, RemainingCount）
  - 有機車位：呼叫 ReportWithMotor（多帶 MTotalCount, MRemainingCount）
成功回應：body 含 <...>true<...>

此檔為「每縣市一個檔案」的完整範例。要接自己的縣市，複製本檔改寫
build_entry() 的 SOAP 格式與欄位宣告即可。
"""

import re

from scheduler.core import net_errors
from scheduler.core.soap import SVC_NS, wrap_envelope

from .base import CityPlugin, CredentialField, ValueField

_DEFAULT_ENDPOINT = (
    "https://tcgis.taichung.gov.tw/PMOTC/ParkingLotsWcf/ParkingLots.svc"
)


class TaichungPlugin(CityPlugin):
    key = "taichung"
    display_name = "臺中市交通局"
    short_name = "臺中市"

    endpoint_env_key = "TAICHUNG_ENDPOINT"
    default_endpoint = _DEFAULT_ENDPOINT

    credential_fields = [
        CredentialField(name="account", env_key="TAICHUNG_ACCOUNT", label="帳號"),
        CredentialField(
            name="password", env_key="TAICHUNG_PASSWORD", label="密碼", secret=True
        ),
    ]

    value_fields = [
        ValueField(key="totalCount", label="總車位"),
        ValueField(key="remainingCount", label="剩餘車位"),
        ValueField(key="mTotalCount", label="機車總車位"),
        ValueField(key="mRemainingCount", label="機車剩餘車位"),
    ]

    # 臺中市官方要求每 10 分鐘補傳一次，故預設啟用定時上傳
    default_enabled = True
    default_interval = 10

    # ------------------------------------------------------------------
    # SOAP 請求格式（核心）
    # ------------------------------------------------------------------

    def build_entry(self, *, enabled, interval_minutes, values, credentials):
        total_count = values.get("totalCount", 0)
        remaining_count = values.get("remainingCount", 0)
        m_total_count = values.get("mTotalCount", 0)
        m_remaining_count = values.get("mRemainingCount", 0)
        account = credentials.get("account", "")
        password = credentials.get("password", "")
        endpoint = credentials.get("endpoint", "") or self.default_endpoint

        # 有機車位時改用 ReportWithMotor
        is_motor = m_total_count > 0
        method = "ReportWithMotor" if is_motor else "Report"

        if is_motor:
            inner = (
                f'<{method} xmlns="{SVC_NS}">'
                f"<Account>{account}</Account>"
                f"<Password>{password}</Password>"
                f"<TotalCount>{total_count}</TotalCount>"
                f"<RemainingCount>{remaining_count}</RemainingCount>"
                f"<MTotalCount>{m_total_count}</MTotalCount>"
                f"<MRemainingCount>{m_remaining_count}</MRemainingCount>"
                f"</{method}>"
            )
        else:
            inner = (
                f'<{method} xmlns="{SVC_NS}">'
                f"<Account>{account}</Account>"
                f"<Password>{password}</Password>"
                f"<TotalCount>{total_count}</TotalCount>"
                f"<RemainingCount>{remaining_count}</RemainingCount>"
                f"</{method}>"
            )

        body_xml = wrap_envelope(inner, "s")

        if is_motor:
            display_label = (
                f"臺中市（汽車 {remaining_count}/{total_count}，"
                f"機車 {m_remaining_count}/{m_total_count}）"
            )
        else:
            display_label = f"臺中市（汽車 {remaining_count}/{total_count}）"

        return {
            "enabled": enabled,
            "intervalMinutes": interval_minutes,
            "values": {
                "totalCount": total_count,
                "remainingCount": remaining_count,
                "mTotalCount": m_total_count,
                "mRemainingCount": m_remaining_count,
            },
            "endpoint": endpoint,
            "soapAction": f"{SVC_NS}IParkingLots/{method}",
            "contentType": "text/xml; charset=utf-8",
            "body": body_xml,
            "successPattern": "true",
            "displayLabel": display_label,
        }

    # ------------------------------------------------------------------
    # 回應 body 解析
    # ------------------------------------------------------------------

    def interpret_body(self, body: str) -> str:
        if not body:
            return "臺中市伺服器未回傳內容"

        # 成功
        if re.search(r">\s*true\s*<", body, re.IGNORECASE):
            return "臺中市上傳成功"

        # 失敗：依文件 debug checklist，最常見為帳密錯誤或資料格式異常
        if re.search(r">\s*false\s*<", body, re.IGNORECASE):
            return (
                "臺中市拒絕上傳資料：最可能的原因如下\n"
                "  1. 帳號或密碼錯誤\n"
                "  2. 車位數格式異常（需為 0~32767 之間的整數）\n"
                "  3. 停車場有機車位但未上傳機車資訊\n"
                "請先至「設定 → 開啟設定檔 (.env)」確認帳密"
            )

        # SOAP Fault
        if net_errors.has_soap_fault(body):
            return f"臺中市伺服器錯誤（SOAP Fault）：{net_errors.extract_soap_fault(body)}"

        return f"臺中市回應異常：{body[:100]}"
