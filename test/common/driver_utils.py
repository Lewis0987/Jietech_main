# -*- coding: utf-8 -*-
"""Chrome Driver 建立與 ChromeOptions。

沿用 IN【V6】.py 已驗證過的 ChromeOptions 設定，並額外處理一個已知問題：

    「Chrome 實際下載位置與 Python 監控位置不同 -> wait_for_download Timeout」

解法是雙保險：
  1) ChromeOptions prefs["download.default_directory"] = download_path
  2) 啟動後再用 CDP Browser/Page.setDownloadBehavior 強制指定同一個 download_path

兩者都吃同一個字串參數，呼叫端只會傳 config.DOWNLOAD_PATH。
"""

import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service


def build_options(download_path, headless=False, extra_args=None):
    """建立 ChromeOptions。download_path 為字串（與 Python 端監控同一個變數）。"""
    download_path = str(download_path)
    Path(download_path).mkdir(parents=True, exist_ok=True)

    options = webdriver.ChromeOptions()
    # --- 沿用 IN【V6】.py 既有設定 ---
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    # --- 降低 console 雜訊（來自 DS.py 的既有做法）---
    options.add_argument("--log-level=3")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    for arg in (extra_args or []):
        options.add_argument(arg)

    prefs = {
        "download.default_directory": download_path,   # 指定下載路徑
        "download.prompt_for_download": False,         # 不跳「另存新檔」
        "download.directory_upgrade": True,            # 資料夾已存在時直接沿用
        "safebrowsing.enabled": True,                  # 避免 Chrome 擋下自動下載
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    options.add_experimental_option("prefs", prefs)
    return options


def force_download_dir(driver, download_path):
    """用 CDP 再次強制下載目錄，避免 prefs 未生效導致檔案落在別的資料夾。

    ⚠️ 實測結論（2026-08-24）：只要呼叫 setDownloadBehavior
    （Page 或 Browser 層級皆然），Chrome 就會把自身的元件 / 擴充套件更新（CRX）
    當成一般下載寫進下載資料夾，產生 downloads.htm*.crdownload 垃圾檔——
    即使頁面只是 about:blank 也會發生。
    對照組：只用 prefs、不呼叫 CDP -> 完全沒有垃圾檔，且下載路徑正常。

    因此 new_driver() 預設【不】呼叫本函式；
    只有實際遇到「Chrome 下載位置與 Python 監控不同」時，
    才用 --force-download-cdp 開啟這個保險。

    回傳實際套用成功的方式名稱；全部失敗回傳 None（不拋例外）。
    """
    download_path = str(download_path)
    Path(download_path).mkdir(parents=True, exist_ok=True)
    for cmd in ("Page.setDownloadBehavior", "Browser.setDownloadBehavior"):
        try:
            driver.execute_cdp_cmd(
                cmd, {"behavior": "allow", "downloadPath": download_path})
            return cmd
        except Exception:
            continue
    return None


def new_driver(download_path, headless=False, page_load_timeout=60,
               maximize=True, extra_args=None, force_cdp=False):
    """建立並回傳 Chrome driver（Selenium Manager 會自動處理 chromedriver）。"""
    options = build_options(download_path, headless=headless, extra_args=extra_args)
    driver = webdriver.Chrome(service=Service(), options=options)
    try:
        driver.set_page_load_timeout(page_load_timeout)
    except Exception:
        pass
    if maximize and not headless:
        try:
            driver.maximize_window()
        except Exception:
            pass
    driver.__download_path__ = str(download_path)
    # 預設不呼叫 CDP：會在使用者的 Downloads 產生 CRX 垃圾檔（見 force_download_dir）
    driver.__download_cdp__ = force_download_dir(driver, download_path) if force_cdp else None
    return driver


def open_url(driver, url, timeout=60):
    """開啟網址並等待 document.readyState == complete。"""
    driver.get(url)
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    return driver.current_url


def browser_info(driver):
    """回傳瀏覽器 / driver 版本，寫進報告 meta 方便追查環境問題。"""
    caps = getattr(driver, "capabilities", {}) or {}
    return {
        "browser": "%s %s" % (caps.get("browserName", "?"), caps.get("browserVersion", "?")),
        "driver": (caps.get("chrome", {}) or {}).get("chromedriverVersion", "?").split(" ")[0],
        "download_cdp": getattr(driver, "__download_cdp__", None),
    }


def quit_driver(driver):
    """安全關閉，任何例外都吞掉。"""
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        pass


def close_extra_windows(driver, keep_handle=None):
    """關閉主視窗以外的分頁（外部連結測試後用），回傳關閉數量。"""
    closed = 0
    try:
        handles = driver.window_handles
    except Exception:
        return 0
    keep = keep_handle or (handles[0] if handles else None)
    for h in list(handles):
        if h == keep:
            continue
        try:
            driver.switch_to.window(h)
            driver.close()
            closed += 1
        except Exception:
            pass
    try:
        if keep:
            driver.switch_to.window(keep)
    except Exception:
        pass
    return closed
