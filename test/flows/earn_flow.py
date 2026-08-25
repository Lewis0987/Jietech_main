# -*- coding: utf-8 -*-
"""[K] EARN / Team Club（/teamClub）。

Phase 7-A 深度 DOM 探查結果（`probe/deep_probe.py --only teamclub`）：
    語意元素：button 13、img 43、a_href 0、input 0、iframe 2（LiveChat）
    可互動元素 194 / 掃描節點 379
    scrollHeight 1166 > viewport 730（頁面可捲動）

實測各功能行為（探查階段確認，未觸碰 Claim / Telegram / WhatsApp / Copy）：

    Tab My Rewards / Invite Rewards / Rules
        div.tab-item + React onClick，同頁切換內容，URL 不變      -> L2
    Club Stars 的 Detail
        導航 -> /subordinateData（含 input[Phone Number] 查詢）    -> L2（只深入一層）
    ic_tips_fill
        點擊後 DOM 無變化（提示型 icon）                           -> L2 記錄
    輪播箭頭 ic_arrow_left_color / ic_arrow_right_color
        左鍵初始 disabled、右鍵可用，可左右還原                     -> L2
    Claim
        實測 disabled=true、cursor=default（新訪客帳號無可領獎勵）  -> L1
    Invite Rewards 分頁的 Claim all                                -> L1
    Rules 分頁的 Invite Now!（導向未經探查確認）                    -> L1
    Invite your friends
        導航 -> 站內 /share 頁（7-D 分類 = A，純站內 Invite 頁）     -> L2
    /share 內的 Whatsapp / Telegram / Save Picture / Copy Link      -> L1
    /teamClub 底部的 Telegram / WhatsApp 圖示                       -> L1

安全原則：
  * Claim / Claim all 絕不點擊；disabled 是正常狀態，不因此判 FAIL。
  * Telegram / WhatsApp 絕不點擊，也不開任何外部分頁。
  * Copy Link / Save Picture 絕不點擊（會改剪貼簿 / 產生下載檔）。
  * 只深入一層（/subordinateData、/share），不再往下鑽。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

EARN_ICON = (By.CSS_SELECTOR, "img[alt='ic_earn_money']")
TEAMCLUB_URL_MARK = "/teamClub"
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")

TABS = ["My Rewards", "Invite Rewards", "Rules"]

CLAIM = (By.XPATH, "//button[normalize-space(.)='Claim']")
CLAIM_ALL = (By.XPATH, "//button[contains(., 'Claim all')]")
INVITE_NOW = (By.XPATH, "//button[contains(., 'Invite Now')]")
INVITE_FRIENDS = (By.XPATH, "//button[contains(., 'Invite your friends')]")
CLUB_DETAIL = (By.XPATH, "(//button[normalize-space(.)='Detail'])[1]")
TIPS = (By.XPATH, "(//button[.//img[@alt='ic_tips_fill']])[1]")
ARROW_RIGHT = (By.XPATH, "//button[.//img[@alt='ic_arrow_right_color']]")
ARROW_LEFT = (By.XPATH, "//button[.//img[@alt='ic_arrow_left_color']]")

# /share 內的分享動作（全部 L1）
SHARE_L1 = [
    ("Whatsapp", (By.XPATH, "//img[contains(@alt,'icon_whatsapp')]"), "外部服務"),
    ("Telegram", (By.XPATH, "//img[contains(@alt,'icon_telegram')]"), "外部服務"),
    ("Save Picture", (By.XPATH, "//img[contains(@alt,'ic_save')]"), "會產生下載檔"),
    ("Copy Link", (By.XPATH, "//img[contains(@alt,'ic_link')]"), "會修改剪貼簿"),
]

# 輪播狀態：左右箭頭的 disabled + 目前顯示的 rebate 數值
CAROUSEL_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
function arrow(alt) {
  return [...document.querySelectorAll('button')]
    .find(b => b.querySelector("img[alt='" + alt + "']")) || null;
}
const l = arrow('ic_arrow_left_color'), r = arrow('ic_arrow_right_color');
// 取出目前可見的 rebate 百分比（輪播每一頁的數值不同）
const vals = [...document.querySelectorAll('span,div')]
  .filter(e => {
    const rc = e.getBoundingClientRect();
    return rc.width > 0 && rc.height > 0 && /^(up to |rebate )?[\d.,₹%]+%?$/.test(t(e.innerText));
  })
  .map(e => t(e.innerText)).slice(0, 12);
return {left_disabled: l ? l.disabled : null,
        right_disabled: r ? r.disabled : null,
        values: vals};
"""

TAB_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
const tabs = [...document.querySelectorAll('div.tab-item')].map(e => ({
  text: t(e.innerText),
  // active 的 tab 內含一張底圖（Tab Active Bottom background）
  active: !!e.querySelector('img'),
  cls: t(e.className).slice(0, 70)
}));
return {tabs: tabs,
        buttons: [...document.querySelectorAll('button')].map(b => t(b.innerText)).filter(Boolean),
        body: t(document.body.innerText).slice(0, 170)};
"""


def _tab(name):
    return (By.XPATH,
            "//div[contains(@class,'tab-item')][normalize-space(.)='%s']" % name)


def _at_teamclub(driver):
    try:
        return TEAMCLUB_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _tab_state(driver):
    try:
        return driver.execute_script(TAB_JS) or {}
    except Exception:
        return {}


def _active_tab(state):
    for t in (state.get("tabs") or []):
        if t.get("active"):
            return t["text"]
    return None


def _goto_earn(ctx, c=None):
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_teamclub(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, EARN_ICON, timeout=cfg.T_NORMAL)
        W.settle(1.5)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_teamclub(driver):
        c.action("已進入 /teamClub")
    return _at_teamclub(driver)


def _ensure_tab(ctx, name):
    """切到指定分頁；回傳是否成功。"""
    W = ctx.W
    driver = ctx.driver
    st = _tab_state(driver)
    if _active_tab(st) == name:
        return True
    try:
        W.safe_click(driver, _tab(name), timeout=ctx.config.T_NORMAL)
        W.settle(1.2)
    except W.SOFT_EXCEPTIONS:
        return False
    return _active_tab(_tab_state(driver)) == name


def _l1(ctx, c, label, locator, reason, timeout=None):
    """只驗證不點擊；不存在則 SKIP。"""
    W = ctx.W
    info = W.probe(ctx.driver, locator, timeout=timeout or ctx.config.T_SHORT)
    if not info["found"]:
        c.skip("本次畫面沒有 %s（NOT PRESENT）" % label)
    c.found("%s 存在：%s" % (label, locator[1]))
    c.check("displayed = %s" % info["displayed"])
    c.check("enabled   = %s" % info["enabled"])
    c.check("clickable = %s" % info["clickable"])
    c.note("[SAFE-L1] 未點擊，原因：%s" % reason)
    return info


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("K", "EARN / Team Club")

    # ============================================================== K-0
    with ctx.case("K-0", "進入 EARN（/teamClub）") as c:
        if not _goto_earn(ctx, c):
            c.skip("無法進入 /teamClub")
        c.check("已進入 %s" % driver.current_url)

        data = dom_scan.scan_interactive(driver, "teamclub", settle=0.8)
        path = dom_scan.save(data, cfg.PROBE_DIR, "teamclub_interactive")
        c.check("可互動元素 %d 個 / 掃描節點 %s（snapshot：%s）"
                % (data["count"], data.get("total_nodes"), path))

        st = _tab_state(driver)
        c.check("分頁：%s（active = %s）"
                % ([t["text"] for t in st.get("tabs", [])], _active_tab(st)))
        c.check("按鈕：%s" % st.get("buttons", [])[:10])

    # ============================================================== K-1 ~ K-3 分頁
    for idx, name in enumerate(TABS, start=1):
        with ctx.case("K-%d" % idx, "分頁 %s" % name) as c:
            if not _goto_earn(ctx):
                c.skip("無法進入 /teamClub")

            before = _tab_state(driver)
            if not any(t["text"] == name for t in before.get("tabs", [])):
                c.skip("找不到分頁 %s" % name)
            already = (_active_tab(before) == name)
            c.found("找到分頁 %s（目前 active = %s）" % (name, _active_tab(before)))

            W.safe_click(driver, _tab(name), timeout=cfg.T_NORMAL)
            c.action("已點擊分頁 %s" % name)
            W.settle(1.3)
            W.note_toast(driver, c)

            after = _tab_state(driver)
            if _active_tab(after) != name:
                raise AssertionError("點擊 %s 後 active 分頁是 %s"
                                     % (name, _active_tab(after)))
            if already:
                c.check("原本就是 active，點擊後仍維持（符合預期）")
            else:
                c.check("active 已切換到 %s" % name)
                if after.get("body") == before.get("body"):
                    raise AssertionError("分頁切換了但內容沒有變化")
                c.check("內容已更新")

            c.check("此分頁按鈕：%s" % after.get("buttons", [])[:8])
            c.note("內容摘要：%s" % after.get("body", "")[:110])

    # ============================================================== K-4 切回
    with ctx.case("K-4", "切回分頁 My Rewards") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        if not _ensure_tab(ctx, "My Rewards"):
            raise AssertionError("無法切回 My Rewards")
        st = _tab_state(driver)
        c.check("active = %s，已恢復初始分頁" % _active_tab(st))

    # ============================================================== K-5 Detail
    with ctx.case("K-5", "Club Stars Detail（/subordinateData）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")

        info = W.probe(driver, CLUB_DETAIL, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("找不到 Club Stars 的 Detail 按鈕")
        c.found("找到 Detail（clickable=%s）" % info["clickable"])

        before_url = driver.current_url
        W.safe_click(driver, CLUB_DETAIL, timeout=cfg.T_NORMAL)
        c.action("已點擊 Detail")
        W.settle(1.5)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
        W.note_toast(driver, c)

        if driver.current_url == before_url:
            raise AssertionError("點擊 Detail 後 URL 沒有變化")
        c.check("已進入內頁：%s" % driver.current_url)

        data = dom_scan.scan(driver, "earn:subordinate", settle=0.8)
        p = dom_scan.save(data, cfg.PROBE_DIR, "earn_subordinate")
        c.check("DOM snapshot：%s" % dom_scan.summarize(data))
        c.note("snapshot 檔案：%s" % p)
        for i in data.get("inputs", []):
            c.check("[L1 不輸入] input type=%r placeholder=%r"
                    % (i.get("type"), i.get("placeholder")))
        texts = [t for t in data.get("texts", []) if t][:6]
        if texts:
            c.note("可見文字：%s" % texts)

        P.close_all(driver)
        if W.exists(driver, BACK_ICON, 0):
            try:
                W.safe_click(driver, BACK_ICON, timeout=cfg.T_SHORT)
                W.settle(1.0)
                c.action("使用站內返回 icon")
            except W.SOFT_EXCEPTIONS:
                pass
        if not _at_teamclub(driver):
            ctx.go_home()
            _goto_earn(ctx)
        if not _at_teamclub(driver):
            raise AssertionError("無法從 /subordinateData 返回 /teamClub")
        c.check("已返回 /teamClub")

    # ============================================================== K-6 tips
    with ctx.case("K-6", "ic_tips_fill 說明 icon") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")

        info = W.probe(driver, TIPS, timeout=cfg.T_SHORT)
        if not info["found"]:
            c.skip("找不到 ic_tips_fill")
        c.found("找到說明 icon（clickable=%s）" % info["clickable"])

        before = _tab_state(driver)
        before_url = driver.current_url
        W.safe_click(driver, TIPS, timeout=cfg.T_NORMAL)
        c.action("已點擊說明 icon")
        W.settle(1.2)
        W.note_toast(driver, c)

        after = _tab_state(driver)
        modal = W.exists(driver, (By.CSS_SELECTOR, "div[class*='z-[1005]']"), 0)
        if modal:
            c.check("開啟說明 modal")
            P.close_all(driver)
            W.settle(0.6)
            c.action("已關閉 modal")
        elif driver.current_url != before_url:
            c.check("URL 已變更：%s" % driver.current_url)
        elif after.get("body") != before.get("body"):
            c.check("頁面內容已變更")
        else:
            c.check("點擊後 DOM 無變化（提示型 icon，可能為 hover 觸發）")

        if not _at_teamclub(driver):
            _goto_earn(ctx)
        c.check("仍在 /teamClub")

    # ============================================================== K-7 輪播
    with ctx.case("K-7", "Rebate 輪播箭頭（左右還原）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")

        right = W.probe(driver, ARROW_RIGHT, timeout=cfg.T_SHORT)
        if not right["found"]:
            c.skip("找不到輪播箭頭")
        left_state = driver.execute_script(
            "const b=[...document.querySelectorAll('button')]"
            ".find(x=>x.querySelector(\"img[alt='ic_arrow_left_color']\"));"
            "return b?b.disabled:null;")
        c.found("找到左右箭頭（左 disabled=%s，右 enabled=%s）"
                % (left_state, right["enabled"]))

        if not right["enabled"]:
            c.skip("右箭頭 disabled，目前只有一頁內容")

        before = driver.execute_script(CAROUSEL_JS)
        c.check("初始狀態：left_disabled=%s right_disabled=%s values=%s"
                % (before["left_disabled"], before["right_disabled"],
                   before["values"][:4]))

        W.safe_click(driver, ARROW_RIGHT, timeout=cfg.T_NORMAL)
        c.action("已點擊右箭頭")
        W.settle(1.5)
        mid = driver.execute_script(CAROUSEL_JS)
        c.check("前進後：left_disabled=%s right_disabled=%s values=%s"
                % (mid["left_disabled"], mid["right_disabled"], mid["values"][:4]))

        advanced = (mid["left_disabled"] != before["left_disabled"]
                    or mid["right_disabled"] != before["right_disabled"]
                    or mid["values"] != before["values"])
        if not advanced:
            raise AssertionError(
                "點擊右箭頭後輪播狀態沒有變化（箭頭 disabled 與數值皆相同）")
        c.check("輪播已前進")

        if not W.exists(driver, ARROW_LEFT, 0):
            raise AssertionError("前進後找不到左箭頭，無法還原")
        W.safe_click(driver, ARROW_LEFT, timeout=cfg.T_NORMAL)
        c.action("已點擊左箭頭（還原）")
        W.settle(1.5)
        after = driver.execute_script(CAROUSEL_JS)
        c.check("還原後：left_disabled=%s right_disabled=%s values=%s"
                % (after["left_disabled"], after["right_disabled"],
                   after["values"][:4]))

        if (after["left_disabled"] != before["left_disabled"]
                or after["values"] != before["values"]):
            raise AssertionError("左右各一次後未回到原本輪播位置")
        c.check("已還原為原本輪播位置")

    # ============================================================== K-8 Claim
    with ctx.case("K-8", "Claim 領取（L1 絕不點擊）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")

        info = _l1(ctx, c, "Claim", CLAIM, "領獎為不可逆操作", timeout=cfg.T_NORMAL)
        state = driver.execute_script(
            "const b=[...document.querySelectorAll('button')]"
            ".find(x=>x.innerText.trim()==='Claim');"
            "return b?{disabled:b.disabled, cursor:getComputedStyle(b).cursor,"
            "parent:(b.parentElement?b.parentElement.innerText:'')"
            ".replace(/\\s+/g,' ').trim().slice(0,60)}:null;")
        if state:
            c.check("Claim 狀態：disabled=%s, cursor=%s"
                    % (state["disabled"], state["cursor"]))
            c.note("周邊資訊：%r" % state["parent"])
            if state["disabled"]:
                c.check("目前為 disabled（無可領取獎勵）— 屬正常狀態，不判 FAIL")
        _ = info

    # ============================================================== K-9 Claim all
    with ctx.case("K-9", "Invite Rewards 的 Claim all（L1）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        if not _ensure_tab(ctx, "Invite Rewards"):
            c.skip("無法切換到 Invite Rewards 分頁")
        _l1(ctx, c, "Claim all", CLAIM_ALL, "批次領獎為不可逆操作")
        _ensure_tab(ctx, "My Rewards")

    # ============================================================== K-10 Invite Now
    with ctx.case("K-10", "Rules 的 Invite Now!（L1）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        if not _ensure_tab(ctx, "Rules"):
            c.skip("無法切換到 Rules 分頁")
        count = driver.execute_script(
            "return [...document.querySelectorAll('button')]"
            ".filter(b=>/Invite Now/.test(b.innerText)).length;")
        _l1(ctx, c, "Invite Now!", INVITE_NOW, "導向未經探查確認，依原則維持 L1")
        c.check("此分頁共有 %s 個 Invite Now! 按鈕" % count)
        _ensure_tab(ctx, "My Rewards")

    # ============================================================== K-11 Invite your friends
    with ctx.case("K-11", "Invite your friends（站內 /share）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")

        info = W.probe(driver, INVITE_FRIENDS, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("找不到 Invite your friends")
        c.found("找到 Invite your friends（clickable=%s）" % info["clickable"])

        before_url = driver.current_url
        handles_before = len(driver.window_handles)
        W.safe_click(driver, INVITE_FRIENDS, timeout=cfg.T_NORMAL)
        c.action("已點擊 Invite your friends")
        W.settle(1.8)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
        W.note_toast(driver, c)

        if len(driver.window_handles) > handles_before:
            urls = []
            for h in driver.window_handles[handles_before:]:
                try:
                    driver.switch_to.window(h)
                    urls.append(driver.current_url)
                    driver.close()
                except Exception:
                    pass
            driver.switch_to.window(driver.window_handles[0])
            raise AssertionError("預期為站內頁，卻開啟了外部分頁：%s（已立即關閉）" % urls)

        if driver.current_url == before_url:
            raise AssertionError("點擊後 URL 沒有變化")
        c.check("[7-D 分類 A] 導向站內頁面：%s" % driver.current_url)

        data = dom_scan.scan(driver, "earn:share", settle=0.8)
        p = dom_scan.save(data, cfg.PROBE_DIR, "earn_share")
        c.check("DOM snapshot：%s" % dom_scan.summarize(data))
        c.note("snapshot 檔案：%s" % p)
        texts = [t for t in data.get("texts", []) if t][:8]
        if texts:
            c.note("可見文字：%s" % texts)

        # /share 內的分享動作全部 L1
        for name, loc, reason in SHARE_L1:
            pr = W.probe(driver, loc, timeout=1)
            if pr["found"]:
                c.check("[L1 不點擊] %s displayed=%s enabled=%s clickable=%s（%s）"
                        % (name, pr["displayed"], pr["enabled"], pr["clickable"], reason))
            else:
                c.note("%s 不存在於此頁" % name)

        P.close_all(driver)
        if W.exists(driver, BACK_ICON, 0):
            try:
                W.safe_click(driver, BACK_ICON, timeout=cfg.T_SHORT)
                W.settle(1.0)
                c.action("使用站內返回 icon")
            except W.SOFT_EXCEPTIONS:
                pass
        if not _at_teamclub(driver):
            ctx.go_home()
            _goto_earn(ctx)
        if not _at_teamclub(driver):
            raise AssertionError("無法從 /share 返回 /teamClub")
        c.check("已返回 /teamClub")

    # ============================================================== K-12 外部連結
    with ctx.case("K-12", "Telegram / WhatsApp（L1 零點擊）") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")

        socials = driver.execute_script(r"""
        const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
        return [...document.querySelectorAll('img')]
          .filter(i => /whatsapp|telegram/i.test((i.alt || '') + (i.className || '')))
          .map(i => {
            const r = i.getBoundingClientRect();
            const p = i.parentElement;
            return {alt: (i.alt || '').split('/').pop(),
                    w: Math.round(r.width), h: Math.round(r.height),
                    parent_cursor: p ? getComputedStyle(p).cursor : '',
                    parent_cls: t(p ? p.className : '').slice(0, 50)};
          });""")
        if not socials:
            c.skip("此頁沒有 Telegram / WhatsApp 圖示")
        c.found("找到外部社群圖示 %d 個" % len(socials))
        for s in socials:
            c.check("%s %sx%s，父層 cursor=%s"
                    % (s["alt"], s["w"], s["h"], s["parent_cursor"]))
        c.note("[SAFE-L1] 未點擊；destination 類型 = 外部通訊軟體（Telegram / WhatsApp）")

        handles = len(driver.window_handles)
        if handles != 1:
            raise AssertionError("不應存在額外分頁，目前有 %d 個" % handles)
        c.check("分頁數 = 1，未開啟任何外部分頁")

    # ============================================================== K-99
    with ctx.case("K-99", "EARN 流程收尾") as c:
        if not _goto_earn(ctx):
            c.skip("無法進入 /teamClub")
        _ensure_tab(ctx, "My Rewards")
        st = _tab_state(driver)
        c.check("結束時 active 分頁 = %s" % _active_tab(st))
        c.check("Claim / Claim all / Invite Now! / Telegram / WhatsApp / Copy Link "
                "/ Save Picture 全程零點擊")
        if len(driver.window_handles) != 1:
            raise AssertionError("結束時分頁數不為 1")
        c.check("分頁數 = 1")

        ctx.go_home()
        if not ctx.R.at_home(driver):
            raise AssertionError("EARN 流程結束後未回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)
