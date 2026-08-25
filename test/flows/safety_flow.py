# -*- coding: utf-8 -*-
"""[E] 破壞性功能安全驗證（L1：只驗證，絕不點擊）。

本 flow 對所有不可逆 / 有金流風險的元素，一律只做：
    Found -> Displayed -> Enabled -> Clickable
**永遠不呼叫 click()**。

涵蓋（locator 全部來自 Phase 3 DOM Probe 實測）：
    Deposit / Withdraw / First Deposit   頭部帳號區
    LiveChat 客服                        浮動泡泡 + iframe
    First recharge 金額鈕 / checkbox     首充 popup 內（僅在 popup 出現時）
    Collect / SPIN / Submit / Redeem     出現時才驗證

元素只在特定 popup 出現時才存在者：未出現 -> SKIP，不算 FAIL。
"""

from selenium.webdriver.common.by import By

# ---------------------------------------------------------------- 大廳常駐
HALL_TARGETS = [
    ("E-1", "Deposit 存款",
     (By.XPATH, "//button[contains(., 'Deposit')][not(contains(., 'First'))]")),
    ("E-2", "Withdraw 提款",
     (By.XPATH, "//button[contains(., 'Withdraw')]")),
    ("E-3", "First Deposit 首儲",
     (By.XPATH, "//button[contains(., 'First Deposit')]")),
    ("E-4", "LiveChat 客服浮動鈕",
     (By.CSS_SELECTOR, "div.adm-floating-bubble-button")),
    # 客服 iframe：#chat-widget 未開啟前寬度為 0，屬正常收合狀態
    ("E-5", "LiveChat iframe",
     (By.CSS_SELECTOR, "iframe#chat-widget, iframe#chat-widget-minimized"), False),
]

# ---------------------------------------------------------------- 首充 popup 內
POPUP_TARGETS = [
    ("E-6", "First recharge 金額 ₹100", (By.XPATH, "//button[contains(., '₹100')]")),
    ("E-7", "First recharge 金額 ₹1,000", (By.XPATH, "//button[contains(., '₹1,000')]")),
    ("E-8", "First recharge checkbox", (By.CSS_SELECTOR, "img[alt='checkbox']")),
]

# ---------------------------------------------------------------- 條件出現
CONDITIONAL_TARGETS = [
    ("E-9", "Collect 領取", (By.XPATH, "//button[contains(., 'Collect')]")),
    ("E-10", "SPIN 轉盤", (By.XPATH, "//span[contains(text(), 'SPIN')]")),
    ("E-11", "Submit 送出", (By.XPATH, "//button[contains(., 'Submit')]")),
    ("E-12", "Redeem 兌換", (By.XPATH, "//button[contains(., 'Redeem')]")),
    ("E-13", "Go to Deposit", (By.XPATH, "//button[contains(., 'Go to Deposit')]")),
]


def _verify_only(ctx, c, label, locator, timeout, require_visible=True):
    """只驗證不點擊；元素不存在則 SKIP。

    require_visible=False 用於「本來就收合 / 隱藏」的元素
    （例如客服 iframe 在未開啟前寬度為 0），此時存在於 DOM 即為通過。
    """
    W = ctx.W
    info = W.probe(ctx.driver, locator, timeout=timeout)
    if not info["found"]:
        c.skip("本次畫面沒有此元素（NOT PRESENT）")
    c.found("%s 存在：%s" % (label, locator[1]))
    c.check("displayed = %s" % info["displayed"])
    c.check("enabled   = %s" % info["enabled"])
    c.check("clickable = %s" % info["clickable"])
    if info["text"]:
        c.note("文字：%r" % info["text"][:40])
    c.note("[SAFE-L1] 本 case 未執行任何點擊")
    if not info["displayed"]:
        if require_visible:
            raise AssertionError("%s 存在但不可見" % label)
        c.note("此元素預設為收合 / 隱藏狀態，存在於 DOM 即視為通過")
    return info


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("E", "破壞性功能安全驗證（只驗證不點擊）")

    if cfg.SAFE_LEVEL > 1:
        ctx.log("警告：SAFE_LEVEL=%s，但 safety_flow 一律以 L1 執行" % cfg.SAFE_LEVEL)

    # ---------------------------------------------------------- 大廳常駐
    if not ctx.R.at_home(driver):
        ctx.go_home()
    P.close_all(driver, log=ctx.log)
    W.settle(0.8)

    for row in HALL_TARGETS:
        case_id, label, locator = row[0], row[1], row[2]
        require_visible = row[3] if len(row) > 3 else True
        with ctx.case(case_id, label) as c:
            _verify_only(ctx, c, label, locator, cfg.T_SHORT,
                         require_visible=require_visible)

    # ---------------------------------------------------------- 首充 popup 內
    # 這些元素只在首充 popup 出現時存在；重新載入大廳讓 popup 有機會彈出。
    ctx.D.open_url(driver, ctx.home_url, timeout=cfg.T_PAGE_LOAD)
    W.settle(2.0)

    # 把佇列推進到首充 popup（只點關閉鈕，不點任何功能按鈕）
    fr_open = False
    for _ in range(6):
        if P.is_open(driver, "first_recharge_vb", timeout=1.0):
            fr_open = True
            break
        if not P.close_once(driver):
            break
        W.settle(1.2)

    for case_id, label, locator in POPUP_TARGETS:
        with ctx.case(case_id, label) as c:
            if not fr_open:
                c.skip("本次首充 popup 未出現（NOT PRESENT）")
            _verify_only(ctx, c, label, locator, cfg.T_SHORT)

    # ---------------------------------------------------------- 條件出現
    for case_id, label, locator in CONDITIONAL_TARGETS:
        with ctx.case(case_id, label) as c:
            _verify_only(ctx, c, label, locator, 1)

    # ---------------------------------------------------------- 收尾
    with ctx.case("E-99", "safety flow 收尾") as c:
        c.check("本 flow 全程未執行任何 click（僅 popup 關閉鈕用於推進佇列）")
        P.close_all(driver, log=ctx.log)
        if not ctx.go_home():
            raise AssertionError("safety flow 結束後無法回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)
