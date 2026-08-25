# -*- coding: utf-8 -*-
"""全站自動化 - 全域設定。

單一事實來源（Single Source of Truth）：
  * 目標網址        -> URL.ini
  * 下載路徑        -> DOWNLOAD_PATH（同一個變數同時給 ChromeOptions 與 download_utils）
  * 破壞性保護等級  -> SAFE_LEVEL
"""

import configparser
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------- 路徑
BASE_DIR = Path(__file__).resolve().parent          # ...\Jietech\test
URL_INI = BASE_DIR / "URL.ini"
OUTPUT_DIR = BASE_DIR / "output"
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"
PROBE_DIR = OUTPUT_DIR / "probe"

# ---------------------------------------------------------------- 目標站台
UI_VERSION = "IN"          # URL.ini 的 section
PRODUCT = "INV6"           # URL.ini 的 key

# 正式環境：禁止任何破壞性操作，也禁止提高 SAFE_LEVEL
PRODUCTION_PRODUCTS = {"INPV6", "7IND"}

# ---------------------------------------------------------------- 下載路徑
# Windows / macOS 皆不寫死使用者名稱
DOWNLOAD_DIR = Path.home() / "Downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_PATH = str(DOWNLOAD_DIR)       # <<< ChromeOptions 與 Python 監控共用這一個字串

# 視為「下載完成」的副檔名（Header 的 APK 下載）
DOWNLOAD_EXTENSIONS = (".apk",)
# 視為「尚未完成」的暫存檔
PARTIAL_SUFFIXES = (".crdownload", ".tmp", ".partial")

# ---------------------------------------------------------------- 破壞性保護
# 1 = 只驗證 found / displayed / enabled，不點擊（預設，唯一支援的等級）
# 2 = 允許可逆操作（Banner / Tab / Popup 開關）— 由各 flow 自行判斷
SAFE_LEVEL = 1

# 一律只驗證、不執行的關鍵字（大小寫不敏感）
DESTRUCTIVE_KEYWORDS = (
    "collect", "claim", "spin", "deposit", "withdraw", "submit", "confirm",
    "redeem", "exchange", "pay", "payment", "recharge", "transfer", "bind",
    "delete", "remove", "logout", "sign out", "send", "change password",
    "reset password", "invite", "share",
)

# ---------------------------------------------------------------- 逾時（秒）
T_SHORT = 3
T_NORMAL = 10
T_LONG = 20
T_PAGE_LOAD = 60
T_DOWNLOAD = 60

# ---------------------------------------------------------------- 執行選項
HEADLESS = False
POPUP_WATCHER = False      # 背景 popup 監控預設關閉（避免與主執行緒搶點擊）


def read_url(ui_version: str = None, product: str = None) -> str:
    """從 URL.ini 讀取目標網址。"""
    ui_version = ui_version or UI_VERSION
    product = product or PRODUCT
    cfg = configparser.ConfigParser()
    if not URL_INI.exists():
        raise FileNotFoundError(f"找不到設定檔：{URL_INI}")
    cfg.read(URL_INI, encoding="utf-8")
    if not cfg.has_section(ui_version):
        raise KeyError(f"URL.ini 沒有 section [{ui_version}]")
    if not cfg.has_option(ui_version, product):
        raise KeyError(f"URL.ini [{ui_version}] 沒有 key {product}")
    return cfg.get(ui_version, product).strip()


def is_production(product: str = None) -> bool:
    return (product or PRODUCT).upper() in PRODUCTION_PRODUCTS


def assert_safe(product: str = None, safe_level: int = None) -> None:
    """正式環境守門：不允許提高破壞性等級。"""
    product = product or PRODUCT
    safe_level = SAFE_LEVEL if safe_level is None else safe_level
    if is_production(product) and safe_level > 1:
        raise RuntimeError(
            f"[SAFETY] {product} 為正式環境，SAFE_LEVEL 必須為 1（目前 {safe_level}）"
        )


def ensure_dirs() -> None:
    for d in (OUTPUT_DIR, SCREENSHOT_DIR, PROBE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def force_utf8_stdout() -> None:
    """避免 Windows cp950 主控台輸出 emoji 時 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def summary() -> str:
    return (
        f"BASE_DIR       : {BASE_DIR}\n"
        f"URL.ini        : {URL_INI} (exists={URL_INI.exists()})\n"
        f"TARGET         : {UI_VERSION}/{PRODUCT}\n"
        f"DOWNLOAD_PATH  : {DOWNLOAD_PATH} (exists={Path(DOWNLOAD_PATH).exists()})\n"
        f"OUTPUT_DIR     : {OUTPUT_DIR}\n"
        f"SAFE_LEVEL     : {SAFE_LEVEL}\n"
        f"IS_PRODUCTION  : {is_production()}"
    )


if __name__ == "__main__":
    force_utf8_stdout()
    ensure_dirs()
    print(summary())
    print(f"URL            : {read_url()}")
