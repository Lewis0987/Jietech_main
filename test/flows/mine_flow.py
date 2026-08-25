# -*- coding: utf-8 -*-
"""[F] MINE 個人中心（/my）。

locator 依據：Phase 4 的 /my DOM snapshot + Phase 5 實際 DOM 確認。
MINE 的每一列都是 <button>，且各自帶一個專屬 icon，
因此用 icon 定位（語言無關、比文字穩定）：

    //button[.//img[@alt='ic_info']]              My info
    //button[.//img[@alt='ic_mission']]           Mission
    //button[.//img[@alt='ic_bank']]              Balance details
    //button[.//img[@alt='ic_customer_support']]  Live support
    //button[.//img[@alt='ic_gift_code']]         Gifts
    //button[.//img[@alt='ic_aboutus']]           Join our community
    //button[.//img[@alt='ic_download_app']]      Download App
    //button[.//img[@alt='ic_reload']]            Refresh to Latest Version
    //button[contains(., 'Logout')]               Logout（無 icon）

Phase 5 探查已確認的實際行為（見報告）：
    My info            -> /account
    Mission            -> /task_center（內含 Claim all / Go，全部 L1）
    Balance details    -> /record
    Live support       -> URL 不變，開啟 LiveChat widget          -> L1 不點
    Gifts              -> 開 modal，含禮包碼 input                -> 不輸入任何內容
    Join our community -> /setting（站內頁，列出 Telegram/Whatsapp）
    Download App       -> 與 Header 同一來源（同樣下載 7ind.apk） -> 只驗入口，不重複下載
    Refresh to Latest  -> 導回 /hall 並重載（可逆、不改帳戶資料）
    Logout             -> L1，絕不點擊

安全原則：進入內頁後若出現 Save / Submit / Delete / Bind / Unbind /
Change Password / Bank / Phone / Email / Redeem / Claim 等字樣，
一律只列出，不操作，也不再往下一層點。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

MINE_ICON = (By.CSS_SELECTOR, "img[alt='ic_user']")
MINE_URL_MARK = "/my"
MODAL = (By.CSS_SELECTOR, "div[class*='z-[1005]']")
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")
CHAT_IFRAME = (By.CSS_SELECTOR, "iframe#chat-widget, iframe#chat-widget-minimized")

# 進入內頁後若出現這些字樣 -> 只列出、不操作
L1_KEYWORDS = ("save", "submit", "delete", "bind", "unbind", "change password",
               "bank", "phone", "email", "redeem", "claim", "confirm",
               "withdraw", "deposit", "logout", "telegram", "whatsapp")


def _row(alt):
    return (By.XPATH, "//button[.//img[@alt='%s']]" % alt)


def _at_my(driver):
    try:
        return MINE_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _goto_my(ctx, c=None):
    """從任何位置回到 /my：先回大廳，再點 TabBar 的 ic_user。"""
    W = ctx.W
    driver = ctx.driver
    if _at_my(driver) and W.exists(driver, MINE_ICON, 0):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, MINE_ICON, timeout=ctx.config.T_NORMAL)
        W.settle(1.2)
        W.wait_ready(driver, timeout=ctx.config.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_my(driver):
        c.action("已回到 /my")
    return _at_my(driver)


def _scan_l1(driver, data, c):
    """從 snapshot 找出需要列為 L1 的元素，只列出不操作。"""
    found = []
    for b in data.get("buttons", []):
        text = (b.get("text") or "").strip()
        low = text.lower()
        if text and any(k in low for k in L1_KEYWORDS):
            found.append(text.replace("\n", " ")[:40])
    for i in data.get("inputs", []):
        found.append("input[type=%s placeholder=%r]"
                     % (i.get("type"), (i.get("placeholder") or "")[:30]))
    if found:
        uniq = []
        for f in found:
            if f not in uniq:
                uniq.append(f)
        c.check("[L1 只列出不操作] %s" % uniq[:10])
    return found


def _visit(ctx, c, label, alt, snap_name, expect_url=None):
    """可逆導航：點擊 -> 驗證內頁 -> snapshot -> 返回 /my -> 驗證。"""
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver

    if not _goto_my(ctx):
        c.skip("無法進入 /my")
    ctx.P.close_all(driver)

    info = W.probe(driver, _row(alt), timeout=cfg.T_NORMAL)
    if not info["found"]:
        c.skip("/my 沒有此項目（img[alt='%s']）" % alt)
    if not info["clickable"]:
        raise AssertionError("%s 不可點擊：%s" % (label, info))
    c.found("找到 %s（text=%r, clickable=%s）"
            % (label, (info["text"] or "").replace("\n", " ")[:30], info["clickable"]))

    before_url = driver.current_url
    W.safe_click(driver, _row(alt), timeout=cfg.T_NORMAL)
    c.action("已點擊 %s" % label)
    W.settle(1.5)
    W.wait_ready(driver, timeout=cfg.T_NORMAL)
    W.note_toast(driver, c)

    after_url = driver.current_url
    if expect_url and expect_url not in after_url:
        raise AssertionError("預期進入 %s，實際是 %s" % (expect_url, after_url))
    if after_url == before_url:
        raise AssertionError("點擊 %s 後 URL 沒有變化" % label)
    c.check("已進入內頁：%s" % after_url)

    data = dom_scan.scan(driver, "mine:%s" % snap_name, settle=1.0)
    path = dom_scan.save(data, cfg.PROBE_DIR, "mine_%s" % snap_name)
    c.check("DOM snapshot：%s" % dom_scan.summarize(data))
    c.note("snapshot 檔案：%s" % path)
    texts = [t for t in data.get("texts", []) if t][:6]
    if texts:
        c.note("可見文字：%s" % texts)
    _scan_l1(driver, data, c)

    # 返回 /my
    if W.exists(driver, BACK_ICON, 0):
        try:
            W.safe_click(driver, BACK_ICON, timeout=cfg.T_SHORT)
            W.settle(1.0)
            c.action("使用站內返回 icon")
        except W.SOFT_EXCEPTIONS:
            pass
    if not _at_my(driver):
        _goto_my(ctx, c)
    if not _at_my(driver):
        raise AssertionError("無法從 %s 返回 /my（目前 %s）" % (label, driver.current_url))
    c.check("已返回 /my")
    return data


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("F", "MINE 個人中心")

    # ============================================================== F-0
    with ctx.case("F-0", "HOME → MINE 進入 /my") as c:
        ctx.go_home()
        P.close_all(driver, log=ctx.log)
        c.found("已在大廳：%s" % driver.current_url)

        info = W.probe(driver, MINE_ICON, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("TabBar 沒有 ic_user")
        W.safe_click(driver, MINE_ICON, timeout=cfg.T_NORMAL)
        c.action("已點擊 TabBar MINE")
        W.settle(1.5)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)

        if not _at_my(driver):
            raise AssertionError("點擊 MINE 後未進入 /my，實際 %s" % driver.current_url)
        c.check("已進入 %s" % driver.current_url)

        rows = driver.execute_script("""
        return [...document.querySelectorAll('button')].map(b => {
          const img = b.querySelector('img');
          return {text: (b.innerText||'').replace(/\\s+/g,' ').trim().slice(0,32),
                  icon: img ? (img.alt||'') : ''};
        }).filter(r => r.text);""")
        c.check("/my 共 %d 個功能列" % len(rows))
        for r in rows:
            c.note("%-30s icon=%s" % (r["text"], r["icon"] or "(無)"))

    # ============================================================== F-1 ~ F-3
    with ctx.case("F-1", "My info 個人資料") as c:
        _visit(ctx, c, "My info", "ic_info", "account", expect_url="/account")

    with ctx.case("F-2", "Mission 任務中心") as c:
        _visit(ctx, c, "Mission", "ic_mission", "task_center", expect_url="/task_center")

    with ctx.case("F-3", "Balance details 帳變明細") as c:
        _visit(ctx, c, "Balance details", "ic_bank", "record", expect_url="/record")

    # ============================================================== F-4 Live support（L1）
    with ctx.case("F-4", "Live support 線上客服（L1 只驗證）") as c:
        if not _goto_my(ctx):
            c.skip("無法進入 /my")
        info = W.probe(driver, _row("ic_customer_support"), timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/my 沒有 Live support")
        c.found("Live support 存在：//button[.//img[@alt='ic_customer_support']]")
        c.check("displayed = %s" % info["displayed"])
        c.check("enabled   = %s" % info["enabled"])
        c.check("clickable = %s" % info["clickable"])

        chat = driver.execute_script("""
        return [...document.querySelectorAll('iframe')].map(f => ({
          id: f.id || '', src: (f.src || '').slice(0, 90),
          w: Math.round(f.getBoundingClientRect().width)}));""")
        c.check("LiveChat iframe 現況：%s" % chat)
        c.note("[SAFE-L1] 未點擊。點擊只會開啟客服視窗，"
               "但關閉需跨網域操作 iframe，且可能觸發真人客服，故不執行")

    # ============================================================== F-5 Gifts
    with ctx.case("F-5", "Gifts 禮包碼") as c:
        if not _goto_my(ctx):
            c.skip("無法進入 /my")
        P.close_all(driver)

        info = W.probe(driver, _row("ic_gift_code"), timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/my 沒有 Gifts")
        c.found("找到 Gifts（clickable=%s）" % info["clickable"])

        W.safe_click(driver, _row("ic_gift_code"), timeout=cfg.T_NORMAL)
        c.action("已點擊 Gifts")
        W.settle(1.2)
        W.note_toast(driver, c)

        if not W.exists(driver, MODAL, cfg.T_SHORT):
            raise AssertionError("點擊 Gifts 後沒有開啟 modal")
        c.check("已開啟禮包碼 modal")

        minfo = P.modal_info(driver)
        if minfo:
            c.note("modal buttons=%s" % (minfo.get("buttons")[:6],))

        data = dom_scan.scan(driver, "mine:gifts", settle=0.8)
        path = dom_scan.save(data, cfg.PROBE_DIR, "mine_gifts")
        c.check("DOM snapshot：%s" % dom_scan.summarize(data))
        c.note("snapshot 檔案：%s" % path)
        for i in data.get("inputs", []):
            c.check("[L1 不輸入] input type=%r placeholder=%r"
                    % (i.get("type"), i.get("placeholder")))
        _scan_l1(driver, data, c)

        # 關閉 modal
        P.close_all(driver)
        W.settle(0.6)
        if W.exists(driver, MODAL, 0):
            raise AssertionError("禮包碼 modal 關不掉")
        c.check("modal 已關閉")
        if not _at_my(driver):
            _goto_my(ctx, c)
        c.check("仍在 /my：%s" % driver.current_url)

    # ============================================================== F-6 Join our community
    with ctx.case("F-6", "Join our community 社群") as c:
        data = _visit(ctx, c, "Join our community", "ic_aboutus", "setting",
                      expect_url="/setting")
        c.note("此為站內頁面，未進入任何外部服務")
        externals = [t for t in data.get("texts", [])
                     if t.lower() in ("telegram", "whatsapp")]
        c.check("[L1 只讀取不點擊] 站內列出的外部社群入口：%s" % (externals or "無"))

    # ============================================================== F-7 Download App
    with ctx.case("F-7", "Download App 下載入口") as c:
        if not _goto_my(ctx):
            c.skip("無法進入 /my")
        info = W.probe(driver, _row("ic_download_app"), timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/my 沒有 Download App")
        c.found("Download App 存在（clickable=%s）" % info["clickable"])
        c.check("displayed = %s / enabled = %s" % (info["displayed"], info["enabled"]))
        c.note("Phase 5 探查確認：此入口與 Header Download 為同一來源"
               "（同樣下載 7ind.apk），APK 端到端已由 B-1 覆蓋")
        c.check("[功能入口驗證] 不重複下載 APK")

    # ============================================================== F-8 Refresh
    with ctx.case("F-8", "Refresh to Latest Version") as c:
        if not _goto_my(ctx):
            c.skip("無法進入 /my")
        P.close_all(driver)

        info = W.probe(driver, _row("ic_reload"), timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/my 沒有 Refresh to Latest Version")
        c.found("找到 Refresh（text=%r）"
                % (info["text"] or "").replace("\n", " ")[:32])

        balance_before = driver.execute_script(
            "const m=document.body.innerText.match(/Player\\d+\\s*([\\d.,]+)/);"
            "return m ? m[1] : null;")
        c.check("點擊前餘額顯示 = %s" % balance_before)

        W.safe_click(driver, _row("ic_reload"), timeout=cfg.T_NORMAL)
        c.action("已點擊 Refresh（僅重載前端快取，不涉及帳戶資料）")
        W.settle(2.0)
        W.wait_ready(driver, timeout=cfg.T_PAGE_LOAD)
        W.note_toast(driver, c)

        if not ctx.R.url_is_home(driver):
            raise AssertionError("Refresh 後未導向大廳，實際 %s" % driver.current_url)
        c.check("已重載並導向大廳：%s" % driver.current_url)

        # 可逆性驗證：回得去 /my，且餘額不變
        P.close_all(driver)
        if not _goto_my(ctx, c):
            raise AssertionError("Refresh 之後無法回到 /my")
        balance_after = driver.execute_script(
            "const m=document.body.innerText.match(/Player\\d+\\s*([\\d.,]+)/);"
            "return m ? m[1] : null;")
        c.check("點擊後餘額顯示 = %s" % balance_after)
        if balance_before is not None and balance_after != balance_before:
            raise AssertionError("Refresh 後餘額顯示改變：%s -> %s"
                                 % (balance_before, balance_after))
        c.check("操作可逆且未改變帳戶資料")

    # ============================================================== F-9 Logout（L1）
    with ctx.case("F-9", "Logout 登出（L1 絕不點擊）") as c:
        if not _goto_my(ctx):
            c.skip("無法進入 /my")
        logout = (By.XPATH, "//button[contains(., 'Logout')]")
        info = W.probe(driver, logout, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/my 沒有 Logout 按鈕")
        c.found("Logout 存在：//button[contains(., 'Logout')]")
        c.check("displayed = %s" % info["displayed"])
        c.check("enabled   = %s" % info["enabled"])
        c.check("clickable = %s" % info["clickable"])
        c.note("[SAFE-L1] 本 case 未執行任何點擊")

        if not _at_my(driver):
            raise AssertionError("Logout 驗證後不應離開 /my，實際 %s" % driver.current_url)
        c.check("仍停留於 /my，確認未登出：%s" % driver.current_url)

    # ============================================================== F-99
    with ctx.case("F-99", "MINE 流程收尾") as c:
        c.check("Logout 全程未被點擊")
        if not ctx.go_home():
            raise AssertionError("MINE 流程結束後無法回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)
