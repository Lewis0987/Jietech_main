# -*- coding: utf-8 -*-
"""WebDriverWait 封裝。

原則（第四階段）：所有等待一律走 WebDriverWait，
只有 UI animation / debounce 才用極短 sleep（settle()）。

locator 一律使用 (By.XPATH, "...") 這種 tuple。
"""

import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT = 10
SHORT_TIMEOUT = 3

# 操作元素時常見、且不該中斷整體流程的例外
SOFT_EXCEPTIONS = (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)


def settle(seconds=0.3):
    """UI 動畫 / debounce 用的極短等待。除此之外不要用 sleep。"""
    time.sleep(seconds)


# ------------------------------------------------------------------ 尋找
def wait_present(driver, locator, timeout=DEFAULT_TIMEOUT, message=""):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator),
        message or "presence timeout: %s" % (locator,),
    )


def wait_visible(driver, locator, timeout=DEFAULT_TIMEOUT, message=""):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located(locator),
        message or "visible timeout: %s" % (locator,),
    )


def wait_clickable(driver, locator, timeout=DEFAULT_TIMEOUT, message=""):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(locator),
        message or "clickable timeout: %s" % (locator,),
    )


def wait_all(driver, locator, timeout=DEFAULT_TIMEOUT, message=""):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located(locator),
        message or "presence_all timeout: %s" % (locator,),
    )


def wait_text(driver, locator, text, timeout=DEFAULT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.text_to_be_present_in_element(locator, text),
        "text '%s' not found in %s" % (text, locator),
    )


def wait_gone(driver, locator, timeout=DEFAULT_TIMEOUT):
    """等待元素消失 / 不可見。回傳 True 表示已消失。"""
    try:
        return bool(WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located(locator)
        ))
    except TimeoutException:
        return False


def wait_url_contains(driver, fragment, timeout=DEFAULT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.url_contains(fragment), "url does not contain '%s'" % fragment
    )


def wait_ready(driver, timeout=DEFAULT_TIMEOUT):
    """等待 document.readyState == complete。"""
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        return False


# ------------------------------------------------------------------ 判斷
def exists(driver, locator, timeout=0):
    """元素是否存在（timeout=0 代表立即檢查，不等待）。"""
    if timeout <= 0:
        try:
            return len(driver.find_elements(*locator)) > 0
        except Exception:
            return False
    try:
        wait_present(driver, locator, timeout)
        return True
    except SOFT_EXCEPTIONS:
        return False


def is_displayed(driver, locator, timeout=0):
    """存在且可見。"""
    try:
        if timeout > 0:
            el = wait_present(driver, locator, timeout)
        else:
            els = driver.find_elements(*locator)
            if not els:
                return False
            el = els[0]
        return bool(el.is_displayed())
    except SOFT_EXCEPTIONS:
        return False


def probe(driver, locator, timeout=SHORT_TIMEOUT):
    """破壞性元素專用：只驗證 found / displayed / enabled / clickable，不點擊。

    回傳 dict：{found, displayed, enabled, clickable, text, tag}
    """
    info = {"found": False, "displayed": False, "enabled": False,
            "clickable": False, "text": "", "tag": ""}
    try:
        el = wait_present(driver, locator, timeout)
    except SOFT_EXCEPTIONS:
        return info
    info["found"] = True
    for key, fn in (("displayed", lambda: el.is_displayed()),
                    ("enabled", lambda: el.is_enabled()),
                    ("text", lambda: (el.text or "").strip()),
                    ("tag", lambda: el.tag_name)):
        try:
            info[key] = fn()
        except Exception:
            pass
    try:
        WebDriverWait(driver, 1).until(EC.element_to_be_clickable(locator))
        info["clickable"] = True
    except SOFT_EXCEPTIONS:
        pass
    return info


# ------------------------------------------------------------------ 操作
def scroll_into_view(driver, element):
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
        settle(0.2)
    except Exception:
        pass
    return element


def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)
    return True


def safe_click(driver, target, timeout=DEFAULT_TIMEOUT, retries=2, use_js_fallback=True):
    """穩定點擊：等待可點擊 -> scroll -> click，被遮擋 / stale 時重試，最後才用 JS。

    target 可以是 locator tuple 或已取得的 WebElement。
    成功回傳被點擊的 element；失敗會拋出最後一個例外（由 case 層攔截）。
    """
    is_locator = isinstance(target, tuple)
    last_exc = None

    for attempt in range(retries + 1):
        try:
            el = wait_clickable(driver, target, timeout) if is_locator else target
            scroll_into_view(driver, el)
            el.click()
            return el
        except (ElementClickInterceptedException, ElementNotInteractableException,
                StaleElementReferenceException) as e:
            last_exc = e
            settle(0.4)
            if attempt == retries and use_js_fallback:
                el = wait_present(driver, target, timeout) if is_locator else target
                scroll_into_view(driver, el)
                js_click(driver, el)
                return el
        except TimeoutException as e:
            last_exc = e
            break

    raise last_exc


def safe_input(driver, locator, text, timeout=DEFAULT_TIMEOUT, clear=True):
    """輸入文字並驗證實際值，回傳 element。"""
    el = wait_visible(driver, locator, timeout)
    scroll_into_view(driver, el)
    if clear:
        try:
            el.clear()
        except Exception:
            pass
    el.send_keys(text)
    actual = el.get_attribute("value")
    if actual is not None and text not in actual:
        raise AssertionError("輸入驗證失敗：預期含 '%s'，實際 '%s'" % (text, actual))
    return el


def text_of(driver, locator, timeout=SHORT_TIMEOUT, default=""):
    try:
        return (wait_present(driver, locator, timeout).text or "").strip()
    except SOFT_EXCEPTIONS:
        return default


def attr_of(driver, locator, name, timeout=SHORT_TIMEOUT, default=""):
    try:
        return wait_present(driver, locator, timeout).get_attribute(name) or default
    except SOFT_EXCEPTIONS:
        return default


# ------------------------------------------------------------------ Toast
# Toast 只是輔助性的 Post-condition：
#   * 抓到 -> 記錄下來，讓報告更有資訊
#   * 沒抓到 -> 不是錯誤，絕對不可因此判 FAIL
# 除非某個功能的規格明確要求一定要有 toast，才由該 case 自行 assert。
_TOAST_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
const sel = "[class*='adm-toast'],[class*='toast'],[class*='Toast'],"
          + "[class*='message'],[class*='Message'],[role='alert'],[role='status']";
const out = [];
document.querySelectorAll(sel).forEach(e => {
  const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  if (r.width <= 0 || r.height <= 0) return;
  if (cs.visibility === 'hidden' || cs.display === 'none') return;
  const text = t(e.innerText);
  if (!text || text.length > 160) return;
  out.push({text: text, cls: t(e.className).slice(0, 80)});
});
return out;
"""


def catch_toast(driver, timeout=2.0, poll=0.25):
    """在 timeout 內嘗試捕捉 toast / 提示訊息。

    回傳 {"text":..., "cls":...} 或 None。
    找不到不是失敗，呼叫端請用 c.note() 記錄即可。
    """
    deadline = time.time() + max(0.0, float(timeout))
    while True:
        try:
            hits = driver.execute_script(_TOAST_JS) or []
        except Exception:
            return None
        if hits:
            return hits[0]
        if time.time() >= deadline:
            return None
        time.sleep(poll)


def note_toast(driver, case_ctx, timeout=2.0, prefix="toast"):
    """便利函式：抓到就記錄，沒抓到就靜靜略過（永遠不拋例外）。"""
    hit = catch_toast(driver, timeout=timeout)
    if hit and case_ctx is not None:
        case_ctx.note("%s：%r" % (prefix, hit["text"][:80]))
    return hit


# ------------------------------------------------------------------ 快捷 locator
def xp(expr):
    return (By.XPATH, expr)


def css(expr):
    return (By.CSS_SELECTOR, expr)


def by_alt(alt, exact=False):
    """img[alt] 是本站最穩定的定位方式（沿用 IN【V6】.py 的做法）。"""
    if exact:
        return (By.CSS_SELECTOR, "img[alt='%s']" % alt)
    return (By.XPATH, "//img[contains(@alt, '%s')]" % alt)


def by_text(text, tag="*"):
    return (By.XPATH, "//%s[contains(text(), '%s')]" % (tag, text))


def by_button_text(text):
    return (By.XPATH, "//button[contains(., '%s')]" % text)
