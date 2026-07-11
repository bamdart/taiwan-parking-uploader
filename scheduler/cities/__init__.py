"""
scheduler/cities/__init__.py - 縣市外掛註冊表

要新增一個縣市：
  1. 複製 taichung.py 改成 <yourcity>.py，實作 CityPlugin 子類別
     （主要改寫 build_entry() 提供該縣市整理後的 SOAP 請求格式）。
  2. 在本檔下方 import 並 register() 一行。

其餘 config / scheduler / GUI 會自動套用新縣市，無需改動。詳見 docs/ADD_A_CITY.md。
"""

from __future__ import annotations

from .base import CityPlugin, CredentialField, ValueField
from .newtaipei import NewTaipeiPlugin
from .taichung import TaichungPlugin

REGISTRY: dict[str, CityPlugin] = {}


def register(plugin: CityPlugin) -> None:
    """把一個縣市外掛加入註冊表。"""
    REGISTRY[plugin.key] = plugin


def get_city(key: str) -> CityPlugin | None:
    """依 key 取得縣市外掛，找不到回傳 None。"""
    return REGISTRY.get(key)


def all_cities() -> list[CityPlugin]:
    """回傳所有已註冊的縣市外掛（順序即註冊順序 = UI 顯示順序）。"""
    return list(REGISTRY.values())


def city_keys() -> list[str]:
    """回傳所有已註冊的縣市 key。"""
    return list(REGISTRY.keys())


# ------------------------------------------------------------------
# 註冊各縣市（順序即 UI 顯示順序）
# ------------------------------------------------------------------

register(TaichungPlugin())
register(NewTaipeiPlugin())

__all__ = [
    "CityPlugin",
    "CredentialField",
    "ValueField",
    "REGISTRY",
    "register",
    "get_city",
    "all_cities",
    "city_keys",
]
