# -*- coding: utf-8 -*-
"""頁面復原：把瀏覽器帶回「穩定頁面」（大廳 /hall）。

每個 case FAIL 之後、以及每個 flow 結束之後都應該呼叫 go_home()，
確保下一個 case 從乾淨的起點開始。

本模組不拋例外，永遠回傳 bool。
"""

from selenium.webdriver.common.by import By

from . import driver_utils as D
from . import popup_utils as P
from . import wait_utils as W

# 大廳的錨點：只要其中一個出現就視為已回到穩定頁面。
# 前三個是 Phase 3 DOM probe 實測「恆存在」的結構性錨點（最可靠），
# 其後為 IN【V6】.py 沿用下來的功能性錨點（會隨活動 / 裝置模式變動）。
STRONG_ANCHORS = [
    (By.CSS_SELECTOR, "header.header-content"),                 # Header 容器
    (By.CSS_SELECTOR, "div.fixed.bottom-0.w-full.z-40"),        # Bottom TabBar 容器
    (By.CSS_SELECTOR, "img[alt='ic_home']"),                    # TabBar HOME icon
]

WEAK_ANCHORS = [
    (By.CSS_SELECTOR, "img[alt='ic_lucky_wheel']"),
    (By.XPATH, "//img[contains(@alt, 'ic_mail')]"),
    (By.XPATH, "//button[contains(., 'Download')]"),
]

HOME_ANCHORS = STRONG_ANCHORS + WEAK_ANCHORS

HOME_URL_MARK = "/hall"


def url_is_home(driver, url_mark=HOME_URL_MARK):
    try:
        return url_mark in (driver.current_url or "")
    except Exception:
        return False


def anchor_found(driver, timeout=0, anchors=None):
    """是否找得到任何一個大廳錨點。"""
    for loc in (anchors or HOME_ANCHORS):
        if W.exists(driver, loc, timeout):
            return True
    return False


def strong_anchor_found(driver, timeout=0):
    """是否找得到結構性錨點（header / bottom tabbar / ic_home）。"""
    return anchor_found(driver, timeout, STRONG_ANCHORS)


def found_anchors(driver):
    """回傳目前命中的錨點清單，供 case 記錄。"""
    return [loc[1] for loc in HOME_ANCHORS if W.exists(driver, loc, 0)]


def at_home(driver, url_mark=HOME_URL_MARK, timeout=0):
    """是否位於大廳。

    ⚠️ URL 才是判斷「在哪一頁」的依據。
    header.header-content / TabBar / ic_home 這些結構性錨點在
    /activity、/teamClub、/my 等每一頁都存在，
    因此只能用來確認「頁面已渲染完成」，不能用來判斷是不是大廳。
    """
    if not url_is_home(driver, url_mark):
        return False
    return anchor_found(driver, timeout)


def go_home(driver, home_url, timeout=20, max_back=2, log=None):
    """把頁面帶回大廳。回傳 True 表示已回到穩定頁面。

    步驟：關閉多餘分頁 -> 關 popup -> back -> 仍不在大廳則直接 get(home_url)
    """
    log = log or (lambda *_a, **_k: None)

    # 1) 只留主視窗（外部連結測試可能開了新分頁）
    try:
        if len(driver.window_handles) > 1:
            n = D.close_extra_windows(driver)
            log("關閉多餘分頁 x%s" % n)
    except Exception:
        pass

    # 2) 關掉擋住畫面的 popup
    try:
        P.close_all(driver, log=log)
    except Exception:
        pass

    # 3) 已經在大廳就結束
    if at_home(driver, timeout=0):
        return True

    # 4) 嘗試上一頁
    for _ in range(max_back):
        try:
            driver.back()
        except Exception:
            break
        W.wait_ready(driver, timeout=timeout)
        W.settle(0.4)
        try:
            P.close_all(driver, log=log)
        except Exception:
            pass
        if at_home(driver, timeout=0):
            log("已用 back 回到大廳")
            return True

    # 5) 最後手段：直接重新載入大廳
    try:
        log("直接載入大廳：%s" % home_url)
        D.open_url(driver, home_url, timeout=timeout)
        W.settle(0.6)
        P.close_all(driver, log=log)
    except Exception as e:
        log("載入大廳失敗：%s" % str(e).split("Stacktrace")[0])
        return False

    # 重新載入之後：URL 必須是大廳，且已渲染出結構性錨點
    return at_home(driver, timeout=W.SHORT_TIMEOUT)


def make_recovery(driver, home_url, log=None):
    """產生給 Reporter.set_recovery() 用的無參數函式。"""
    def _recover():
        go_home(driver, home_url, log=log)
    return _recover
