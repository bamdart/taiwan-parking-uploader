"""
scheduler/cities/base.py - 縣市外掛基底

定義 CityPlugin 介面與 CredentialField / ValueField 宣告型別。
本檔不 import Qt，純資料 + 函式，方便獨立測試與 fork。

要新增一個縣市：複製 taichung.py 改成 <yourcity>.py，主要改寫 build_entry()
提供該縣市「整理後的 SOAP 請求格式」，並在 __init__.py 註冊一行。
詳見 docs/ADD_A_CITY.md。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CredentialField:
    """一個帳密欄位的宣告（供設定精靈建立輸入欄、config 讀寫 .env）。"""

    name: str             # build_entry 收到的 credentials dict 的 key，如 "account"
    env_key: str          # .env 中的 key，如 "TAICHUNG_ACCOUNT"
    label: str            # UI 顯示標籤，如 "帳號"
    secret: bool = False  # True 時 UI 用密碼遮罩


@dataclass(frozen=True)
class ValueField:
    """一個車位數欄位的宣告（供狀態卡片建立數字輸入欄）。"""

    key: str              # schedule values 中的 key，如 "totalCount"
    label: str            # UI 顯示標籤，如 "總車位"
    blank_value: int | None = None  # 允許留空：留空時送出此值（如臺北市無此車種送 -9）；None = 不可留空，空白視為 0


class CityPlugin:
    """縣市外掛基底。

    子類別以 class 屬性宣告識別/欄位，並實作 build_entry()（核心：SOAP 格式）
    與 interpret_body()（該縣市回應解析）。
    """

    # --- 識別 ---
    key: str = ""                 # schedule.json 中的城市 key，如 "taichung"
    display_name: str = ""        # UI 顯示（主管機關全名），如 "臺中市交通局"
    short_name: str = ""          # 訊息用短名，如 "臺中市"

    # --- Endpoint ---
    endpoint_env_key: str = ""    # .env 中 endpoint 的 key
    default_endpoint: str = ""    # 未設定時的預設 endpoint

    # --- 欄位宣告 ---
    credential_fields: list[CredentialField] = field(default_factory=list)
    value_fields: list[ValueField] = field(default_factory=list)

    # --- 預設排程 ---
    default_enabled: bool = True
    default_interval: int = 10

    # ------------------------------------------------------------------
    # 子類別必須實作
    # ------------------------------------------------------------------

    def build_entry(
        self,
        *,
        enabled: bool,
        interval_minutes: int,
        values: dict,
        credentials: dict,
    ) -> dict:
        """組裝寫入 schedule.json 的完整 entry。

        回傳的 dict 需包含排程器 POST 所需的全部欄位：
        endpoint / soapAction / contentType / body / successPattern / displayLabel，
        以及 enabled / intervalMinutes / values。排程器會原封不動送出。
        非 SOAP 服務 soapAction 給空字串；需額外 header（如 API Key）時帶 headers。

        credentials 為 config 依 credential_fields 組出的 dict（key 為各
        CredentialField.name），另含 "endpoint" 一項。
        """
        raise NotImplementedError

    def interpret_body(self, body: str) -> str:
        """解析該縣市服務的回應 body，回傳使用者友善訊息。

        只需處理該縣市服務專屬的成功/失敗判讀；網路層與 HTTP 層錯誤已由
        core/net_errors.py 的通用流程處理，不會進到這裡。
        """
        raise NotImplementedError
