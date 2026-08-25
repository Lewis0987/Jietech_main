# -*- coding: utf-8 -*-
"""Popup / Modal 偵測與關閉。

取代 IN【V6】.py 中重複貼上 8 次的「首充內彈關閉」程式碼。
locator 全部沿用 IN【V6】.py 已驗證過的寫法，不做無謂替換。

注意：IN【V6】.py 的背景執行緒 handle_popups() 找到關閉鈕後
沒有呼叫 .click()（第 79 行只做賦值），實際上是無效的。
這裡的 PopupWatcher 修正了這個問題，但預設關閉
（config.POPUP_WATCHER = False），避免背景執行緒與主流程搶點擊。
"""

import threading
import time

from selenium.webdriver.common.by import By

from . import wait_utils as W

# ------------------------------------------------------------------ 關閉鈕
# 順序即優先順序。
# 刻意不包含 ic_close_2：那是 Header 的下載列關閉鈕，
# 屬於 header_flow 的測試目標（B-1-2），不可被通用 popup 清理提前關掉。
CLOSE_LOCATORS = [
    (By.CSS_SELECTOR, "img[alt='ic_close']"),
    (By.XPATH, "//img[contains(@alt, 'ic_close') and not(contains(@alt, 'ic_close_2'))]"),
    (By.XPATH, "//button[contains(text(), 'Later')]"),
]

# 下載列關閉鈕，交給 header_flow 明確處理
DOWNLOAD_BAR_CLOSE = (By.CSS_SELECTOR, "img[alt='ic_close_2']")

# ------------------------------------------------------------------ 通用 modal
# Phase 3 實測：本站所有 popup 共用同一個 modal 容器 div[class*='z-[1005]']，
# 內含 img[alt='ic_close']。
# ⚠️ 這個錨點【只能用來判斷「目前存在 modal」】，
#    不可因為看到 modal 就直接亂關；仍須先識別是哪一種 popup 再對應處理。
MODAL = (By.CSS_SELECTOR, "div[class*='z-[1005]']")


def modal_present(driver, timeout=0):
    """目前畫面上是否存在 modal（僅判斷，不做任何關閉動作）。"""
    return W.is_displayed(driver, MODAL, timeout)


def modal_info(driver):
    """讀取目前 modal 的特徵（圖片 alt / 按鈕文字 / 前 120 字），僅供辨識與記錄。"""
    js = """
    const m = document.querySelector("div[class*='z-[1005]']");
    if (!m) return null;
    const t = s => (s || '').toString().replace(/\\s+/g, ' ').trim();
    return {
      imgs: [...m.querySelectorAll('img')].map(i => i.alt || '').filter(Boolean).slice(0, 12),
      buttons: [...m.querySelectorAll('button')].map(b => t(b.innerText)).filter(Boolean).slice(0, 10),
      text: t(m.innerText).slice(0, 120)
    };
    """
    try:
        return driver.execute_script(js)
    except Exception:
        return None

# ------------------------------------------------------------------ 已知 popup
# key / 中文說明 / 偵測 locator（全部來自 IN【V6】.py）
KNOWN_POPUPS = [
    {"key": "subscribe", "label": "訂閱 Subscribe",
     "locator": (By.XPATH, "//button[contains(text(), 'Later')]"),
     "close": (By.XPATH, "//button[contains(text(), 'Later')]")},

    {"key": "prize_wheel", "label": "充值大輪盤",
     "locator": (By.XPATH, "//span[contains(text(), 'SPIN')]"), "close": None},

    {"key": "first_recharge_vb", "label": "首充 popup",
     "locator": (By.XPATH, "//img[contains(@alt, 'popup_first_recharge_vb')]"), "close": None},

    {"key": "first_recharge", "label": "首充內彈",
     "locator": (By.XPATH, "//img[contains(@alt, 'first_recharge_popup')]"), "close": None},

    {"key": "mission", "label": "任務中心",
     # Phase 3 實測改用「內容特徵」定位：modal 內含 img[alt='ic_task']。
     # 舊版 //div[contains(@class,'p-4 box-border')] 是版面 class，過於脆弱，已停用。
     "locator": (By.XPATH,
                 "//div[contains(@class, 'z-[1005]')][.//img[@alt='ic_task']]"),
     # 備援：任務彈窗固定有 View All Tasks 按鈕
     "alt_locator": (By.XPATH, "//button[contains(., 'View All Tasks')]"),
     "close": None},

    {"key": "club", "label": "俱樂部",
     "locator": (By.XPATH, "//img[contains(@alt, 'popup_club')]"), "close": None},

    {"key": "telegram", "label": "Telegram 訂閱",
     "locator": (By.XPATH, "//img[contains(@alt, 'popup_subscribe_telegram')]"), "close": None},

    {"key": "jackpot", "label": "Jackpot",
     "locator": (By.XPATH, "//img[contains(@alt, 'popup_jackpot')]"), "close": None},
]

POPUP_BY_KEY = dict((p["key"], p) for p in KNOWN_POPUPS)


# ------------------------------------------------------------------ 偵測
def popup_visible(driver, popup, timeout=0):
    """主 locator 或備援 locator 任一可見即視為該 popup 存在。"""
    if W.is_displayed(driver, popup["locator"], timeout):
        return True
    alt = popup.get("alt_locator")
    return bool(alt) and W.is_displayed(driver, alt, 0)


def detect(driver, timeout=0):
    """回傳目前畫面上偵測到的 popup key 清單（不點擊）。

    以「整批輪詢」取代逐一 WebDriverWait，
    否則 8 個 locator x timeout 會累加成數十秒。
    """
    deadline = time.time() + max(0.0, float(timeout))
    while True:
        found = [p["key"] for p in KNOWN_POPUPS if popup_visible(driver, p, 0)]
        if found or time.time() >= deadline:
            return found
        time.sleep(0.3)


def has_close_button(driver):
    """畫面上是否還有可見的 popup 關閉鈕。"""
    for loc in CLOSE_LOCATORS:
        try:
            if any(el.is_displayed() for el in driver.find_elements(*loc)):
                return True
        except Exception:
            continue
    return False


def is_open(driver, key, timeout=0):
    p = POPUP_BY_KEY.get(key)
    return bool(p) and popup_visible(driver, p, timeout)


# ------------------------------------------------------------------ 關閉
def _click_first_visible(driver, locators):
    """點擊第一個可見的關閉鈕，回傳使用的 locator；沒有則回傳 None。"""
    for loc in locators:
        try:
            elements = driver.find_elements(*loc)
        except Exception:
            continue
        for el in elements:
            try:
                if not el.is_displayed():
                    continue
                W.scroll_into_view(driver, el)
                try:
                    el.click()
                except Exception:
                    W.js_click(driver, el)
                return loc
            except W.SOFT_EXCEPTIONS:
                continue
            except Exception:
                continue
    return None


def close_once(driver):
    """關閉一個 popup，回傳所用的 locator 或 None。"""
    return _click_first_visible(driver, CLOSE_LOCATORS)


def close_all(driver, max_rounds=8, settle=0.35, log=None):
    """連續關閉畫面上的 popup，回傳關閉次數。

    本站 popup 會「排隊」連續彈出（關掉一個馬上出現下一個），
    因此需要多輪；沒有關閉鈕就立即停止，不會空轉。
    絕不拋例外——popup 關不掉不應該讓任何 case 失敗。
    """
    log = log or (lambda *_a, **_k: None)
    closed = 0
    for _ in range(max_rounds):
        try:
            used = close_once(driver)
        except Exception:
            break
        if not used:
            break
        closed += 1
        log("關閉 popup（%s）" % (used[1],))
        W.settle(settle)
        try:
            if not has_close_button(driver):
                break
        except Exception:
            break
    return closed


def close_specific(driver, key, timeout=W.SHORT_TIMEOUT):
    """關閉指定 popup。回傳 True 表示原本存在且已關閉。"""
    p = POPUP_BY_KEY.get(key)
    if not p:
        return False
    if not popup_visible(driver, p, timeout):
        return False
    close_loc = p.get("close")
    used = _click_first_visible(driver, [close_loc] if close_loc else CLOSE_LOCATORS)
    if not used:
        return False
    W.settle(0.35)
    return not popup_visible(driver, p, 0)


# ------------------------------------------------------------------ 背景監控
class PopupWatcher(threading.Thread):
    """背景關閉突然彈出的 popup（預設不啟用）。

    與 IN【V6】.py 的差異：真的會 click，且不會因為找不到元素而丟例外。
    """

    def __init__(self, driver, interval=2.0, log=None):
        super().__init__(daemon=True)
        self.driver = driver
        self.interval = interval
        self.log = log or (lambda *_a, **_k: None)
        self._stop = threading.Event()
        self.closed_count = 0

    def run(self):
        while not self._stop.is_set():
            try:
                if close_once(self.driver):
                    self.closed_count += 1
                    self.log("背景關閉 popup")
            except Exception:
                # session 失效等狀況直接結束，不干擾主流程
                break
            self._stop.wait(self.interval)

    def stop(self, timeout=5):
        self._stop.set()
        try:
            self.join(timeout)
        except Exception:
            pass
        return self.closed_count
