# -*- coding: utf-8 -*-
"""[D] 首頁導覽 / 選單 / 分類 / 搜尋 / 跑馬燈 / 音量。

全部 locator 來自 Phase 3 DOM Probe 實測，沒有任何猜測：
    Bottom TabBar  div.fixed.bottom-0.w-full.z-40
        HOME   img[alt='ic_home']
        PROMO  img[alt='ic_activity']
        中央   img[alt='nav_bar_invitation_wheel']
        EARN   img[alt='ic_earn_money']
        MINE   img[alt='ic_user']
    遊戲分類（左側欄）img[alt='ic_popular'|'ic_slots'|'ic_original'|
                        'ic_casino'|'ic_game'|'ic_fishing'|'ic_sports']
    Search        //button[contains(.,'Search')] + img[alt='ic_search_white']
    公告跑馬燈     div.swiper.swiper-vertical
    音量          img[alt='ic_volume']

安全原則：
  * 只做導覽 / 切換，不點遊戲卡片（避免進入實際遊戲或下注）。
  * 不執行 SPIN / Collect / Deposit / Withdraw（由 safety_flow 只驗證）。
  * D-15 音量會點擊，但必須「點兩次還原」，不留下永久設定變更。

Phase 4-C：PROMO / EARN / MINE 進入後會輸出 DOM snapshot 到
           output/probe/snapshot_<name>_<ts>.json，供下一階段使用。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

TABBAR = (By.CSS_SELECTOR, "div.fixed.bottom-0.w-full.z-40")
HOME_ICON = (By.CSS_SELECTOR, "img[alt='ic_home']")
SEARCH_BTN = (By.XPATH, "//button[contains(., 'Search')]")
SEARCH_ICON = (By.CSS_SELECTOR, "img[alt='ic_search_white']")
MARQUEE = (By.CSS_SELECTOR, "div.swiper.swiper-vertical")
VOLUME = (By.CSS_SELECTOR, "img[alt='ic_volume']")
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")
MODAL = (By.CSS_SELECTOR, "div[class*='z-[1005]']")

# D-2 ~ D-5：底部導覽（需要輸出內頁 snapshot 的標記為 snapshot=True）
NAV_CASES = [
    ("D-2", "PROMO 活動", "ic_activity", "promo", True),
    ("D-3", "Invitation Wheel 邀請轉盤", "nav_bar_invitation_wheel", "invite_wheel", False),
    ("D-4", "EARN 賺錢 / 邀請", "ic_earn_money", "earn", True),
    ("D-5", "MINE 個人中心", "ic_user", "mine", True),
]

# D-6 ~ D-12：遊戲分類
CATEGORIES = [
    ("D-6", "ic_popular", "熱門"),
    ("D-7", "ic_slots", "老虎機"),
    ("D-8", "ic_original", "原創"),
    ("D-9", "ic_casino", "真人娛樂場"),
    ("D-10", "ic_game", "遊戲"),
    ("D-11", "ic_fishing", "捕魚"),
    ("D-12", "ic_sports", "體育"),
]


def _icon(alt):
    return (By.CSS_SELECTOR, "img[alt='%s']" % alt)


CAT_CLASS_JS = """
const alts = arguments[0];
const out = {};
alts.forEach(a => {
  const e = document.querySelector("img[alt='" + a + "']");
  if (e && e.parentElement) out[a] = (e.parentElement.className || '').toString();
});
return out;
"""


def _category_classes(driver):
    """取得每個分類 icon 父層的 class（active 樣式就在這一層）。"""
    try:
        return driver.execute_script(CAT_CLASS_JS, [alt for _, alt, _ in CATEGORIES]) or {}
    except Exception:
        return {}


def _normalize_cat_class(alt, cls):
    """去掉每個分類各自的 icon-ic_xxx token，讓不同分類之間可以互相比較。

    實測 class 形如：
        icon mode-3 icon-ic_slots w-full h-full rounded-lg border
        bgi-border-[var(--transparent-white-20)]
    目前選中的分類會多一段 border 樣式（bgi-border-[var(--base-1-variant5)]）。
    這裡不寫死那個 token，改用「去掉自身 icon token 後與多數不同」來判斷。
    """
    return " ".join(t for t in (cls or "").split() if t != "icon-%s" % alt)


def _active_category(classes):
    """回傳目前 active 的分類 alt；無法判斷時回傳 None。"""
    if len(classes) < 3:
        return None
    norm = dict((alt, _normalize_cat_class(alt, cls)) for alt, cls in classes.items())
    counts = {}
    for cls in norm.values():
        counts[cls] = counts.get(cls, 0) + 1
    common = max(counts, key=counts.get)
    odd = [alt for alt, cls in norm.items() if cls != common]
    return odd[0] if len(odd) == 1 else None


def _page_signature(driver):
    """用來判斷「頁面是否真的切換」的輕量指紋（不點擊）。"""
    js = """
    const t = s => (s || '').toString().replace(/\\s+/g, ' ').trim();
    return {
      url: location.href,
      imgs: document.querySelectorAll('img').length,
      buttons: document.querySelectorAll('button').length,
      head: t(document.body.innerText).slice(0, 160)
    };
    """
    try:
        return driver.execute_script(js)
    except Exception:
        return {"url": driver.current_url, "imgs": 0, "buttons": 0, "head": ""}


def _changed(before, after):
    """頁面是否發生合理變化。"""
    if before["url"] != after["url"]:
        return "URL 變更 %s -> %s" % (before["url"], after["url"])
    if before["head"] != after["head"]:
        return "頁面內容變更"
    if abs(before["imgs"] - after["imgs"]) >= 3 or before["buttons"] != after["buttons"]:
        return "元素組成變更（img %s->%s, button %s->%s）" % (
            before["imgs"], after["imgs"], before["buttons"], after["buttons"])
    return None


def _back_home(ctx, c):
    """回大廳：優先站內返回鍵，其次 recovery。"""
    W, driver = ctx.W, ctx.driver
    if W.exists(driver, BACK_ICON, 0):
        try:
            W.safe_click(driver, BACK_ICON, timeout=ctx.config.T_SHORT)
            W.settle(0.8)
            c.action("使用站內返回 icon")
        except W.SOFT_EXCEPTIONS:
            pass
    if not ctx.R.at_home(ctx.driver):
        if ctx.W.exists(ctx.driver, HOME_ICON, 0):
            try:
                ctx.W.safe_click(ctx.driver, HOME_ICON, timeout=ctx.config.T_SHORT)
                ctx.W.settle(0.8)
                c.action("點擊 TabBar HOME")
            except ctx.W.SOFT_EXCEPTIONS:
                pass
    if not ctx.R.at_home(ctx.driver):
        ctx.go_home()
    return ctx.R.at_home(ctx.driver)


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("D", "導覽 / 選單 / 分類 / 搜尋")

    if not ctx.R.at_home(driver):
        ctx.go_home()
    P.close_all(driver, log=ctx.log)
    W.settle(1.0)

    # ============================================================== D-1 HOME
    with ctx.case("D-1", "TabBar HOME") as c:
        if not W.exists(driver, TABBAR, cfg.T_NORMAL):
            c.skip("找不到 Bottom TabBar 容器")
        c.found("找到 TabBar 容器 div.fixed.bottom-0.w-full.z-40")

        info = W.probe(driver, HOME_ICON, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("TabBar 沒有 ic_home")
        if not info["clickable"]:
            raise AssertionError("ic_home 不可點擊：%s" % info)
        c.found("找到 HOME icon（clickable=%s）" % info["clickable"])

        W.safe_click(driver, HOME_ICON, timeout=cfg.T_NORMAL)
        c.action("已點擊 HOME")
        W.settle(1.0)
        P.close_all(driver)

        if not ctx.R.strong_anchor_found(driver, timeout=cfg.T_SHORT):
            raise AssertionError("點擊 HOME 後找不到大廳結構性錨點")
        c.check("仍在大廳，命中錨點：%s" % ctx.R.found_anchors(driver)[:3])

    # ============================================================== D-2 ~ D-5
    for case_id, label, alt, snap_name, want_snapshot in NAV_CASES:
        with ctx.case(case_id, label) as c:
            if not _back_home(ctx, c):
                c.skip("無法回到大廳，略過本項")
            P.close_all(driver)

            locator = _icon(alt)
            info = W.probe(driver, locator, timeout=cfg.T_NORMAL)
            if not info["found"]:
                c.skip("TabBar 沒有 %s" % alt)
            if not info["clickable"]:
                raise AssertionError("%s 不可點擊：%s" % (alt, info))
            c.found("找到 %s（clickable=%s）" % (alt, info["clickable"]))

            before = _page_signature(driver)
            W.safe_click(driver, locator, timeout=cfg.T_NORMAL)
            c.action("已點擊 %s" % alt)
            W.settle(1.5)
            W.wait_ready(driver, timeout=cfg.T_NORMAL)

            after = _page_signature(driver)
            reason = _changed(before, after)
            if not reason:
                raise AssertionError("點擊 %s 後頁面沒有任何變化" % alt)
            c.check("頁面已切換：%s" % reason)

            # 破壞性元素：只記錄，不點擊
            if W.exists(driver, MODAL, 0):
                minfo = P.modal_info(driver)
                if minfo:
                    c.note("開啟了 modal：buttons=%s" % (minfo.get("buttons")[:6],))

            # ---------- Phase 4-C：內頁 DOM snapshot ----------
            if want_snapshot:
                data = dom_scan.scan(driver, "menu:%s" % snap_name, settle=1.0)
                path = dom_scan.save(data, cfg.PROBE_DIR, snap_name)
                c.check("DOM snapshot：%s" % dom_scan.summarize(data))
                c.note("snapshot 檔案：%s" % path)
                texts = [t for t in data.get("texts", []) if t][:8]
                if texts:
                    c.note("可見文字：%s" % texts)

            if not _back_home(ctx, c):
                raise AssertionError("無法從 %s 返回大廳" % label)
            c.check("已返回大廳：%s" % driver.current_url)

    # ============================================================== D-6 ~ D-12
    for case_id, alt, zh in CATEGORIES:
        with ctx.case(case_id, "遊戲分類 %s（%s）" % (alt, zh)) as c:
            if not _back_home(ctx, c):
                c.skip("無法回到大廳，略過本項")
            P.close_all(driver)

            locator = _icon(alt)
            info = W.probe(driver, locator, timeout=cfg.T_SHORT)
            if not info["found"]:
                c.skip("此環境沒有分類 %s" % alt)
            if not info["clickable"]:
                raise AssertionError("%s 不可點擊：%s" % (alt, info))
            c.found("找到分類 %s（clickable=%s）" % (alt, info["clickable"]))

            before = _page_signature(driver)
            before_classes = _category_classes(driver)
            before_parent = before_classes.get(alt, "")
            already_active = (_active_category(before_classes) == alt)
            if already_active:
                c.check("此分類目前已是 active（進入大廳的預設分類）")

            W.safe_click(driver, locator, timeout=cfg.T_NORMAL)
            c.action("已點擊分類 %s" % alt)
            W.settle(1.2)

            after = _page_signature(driver)
            after_classes = _category_classes(driver)
            after_parent = after_classes.get(alt, "")

            # Post-condition
            if already_active:
                # 點擊本來就選中的分類：正確行為是「維持 active」，而不是切換
                if _active_category(after_classes) != alt:
                    raise AssertionError(
                        "點擊已 active 的分類 %s 後，active 狀態反而跑掉了" % alt)
                c.check("點擊後仍維持 active（符合預期，非狀態切換）")
            elif after_parent != before_parent:
                c.check("分類 active 樣式已變更")
            else:
                reason = _changed(before, after)
                if reason:
                    c.check("遊戲列表已變化：%s" % reason)
                else:
                    raise AssertionError(
                        "點擊分類 %s 後 active 樣式與遊戲列表都沒有變化" % alt)
            c.note("不點擊遊戲卡片，避免進入實際遊戲")

    # ============================================================== D-13 Search
    with ctx.case("D-13", "Search 搜尋") as c:
        if not _back_home(ctx, c):
            c.skip("無法回到大廳")
        P.close_all(driver)

        info = W.probe(driver, SEARCH_BTN, timeout=cfg.T_NORMAL)
        if not info["found"]:
            info = W.probe(driver, SEARCH_ICON, timeout=cfg.T_SHORT)
            if not info["found"]:
                c.skip("找不到 Search 入口")
            target = SEARCH_ICON
        else:
            target = SEARCH_BTN
        c.found("找到 Search 入口（clickable=%s）" % info["clickable"])

        before = _page_signature(driver)
        before_inputs = driver.execute_script("return document.querySelectorAll('input').length")
        c.check("點擊前 input 數量 = %s" % before_inputs)

        W.safe_click(driver, target, timeout=cfg.T_NORMAL)
        c.action("已點擊 Search")
        W.settle(1.2)

        # Phase 3 已確認首頁沒有 input，點擊後重新檢查 DOM
        found_inputs = driver.execute_script("""
        return [...document.querySelectorAll('input')].map(e => ({
          type: (e.type||'').toLowerCase(), name: e.name||'',
          placeholder: e.placeholder||'',
          cls: (e.className||'').toString().slice(0,70),
          visible: e.getBoundingClientRect().width > 0
        }));""")
        after = _page_signature(driver)

        if found_inputs:
            c.check("Search UI 已開啟，出現 %d 個 input" % len(found_inputs))
            for f in found_inputs[:3]:
                c.note("input type=%r placeholder=%r cls=%s"
                       % (f["type"], f["placeholder"], f["cls"]))
            c.note("本階段僅驗證 UI 開啟，不輸入任何資料")
        else:
            reason = _changed(before, after)
            if not reason:
                raise AssertionError("點擊 Search 後沒有出現 input，畫面也沒有變化")
            c.check("Search UI 已開啟（無 input，%s）" % reason)

        # 關閉 Search 並驗證回到大廳
        if W.exists(driver, BACK_ICON, 0) or P.has_close_button(driver):
            _back_home(ctx, c)
        else:
            ctx.go_home()
        if not ctx.R.strong_anchor_found(driver, timeout=cfg.T_SHORT):
            raise AssertionError("關閉 Search 後未回到大廳")
        c.check("已關閉 Search 並回到大廳")

    # ============================================================== D-14 跑馬燈
    with ctx.case("D-14", "公告跑馬燈") as c:
        if not _back_home(ctx, c):
            c.skip("無法回到大廳")
        if not W.exists(driver, MARQUEE, cfg.T_NORMAL):
            c.skip("找不到公告跑馬燈容器")
        c.found("找到跑馬燈容器 div.swiper.swiper-vertical")

        slides = driver.execute_script(
            "const s=document.querySelector('div.swiper.swiper-vertical');"
            "return s ? s.querySelectorAll('.swiper-slide').length : 0;")
        c.check("公告則數 = %s" % slides)

        # popup 蓋住時 Selenium 的 .text 會是空字串，
        # 因此先關 popup，並改用 JS textContent（不受可視區影響）多試幾次。
        text = ""
        for _ in range(3):
            P.close_all(driver)
            text = (driver.execute_script(
                "const s=document.querySelector('div.swiper.swiper-vertical');"
                "return s ? (s.innerText || s.textContent || '') : '';") or "").strip()
            if text:
                break
            W.settle(1.0)

        if not text:
            raise AssertionError("跑馬燈容器存在但沒有任何可讀內容")
        # 內容本來就會變動，只驗證「讀得到」，不比對文字
        c.check("讀取到公告內容（%d 字）：%s" % (len(text), text[:60]))

    # ============================================================== D-15 音量
    with ctx.case("D-15", "ic_volume 圖示（點擊後還原）") as c:
        info = W.probe(driver, VOLUME, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("找不到 ic_volume")
        if not info["clickable"]:
            raise AssertionError("ic_volume 不可點擊：%s" % info)

        state_js = """
        const e = document.querySelector("img[alt*='volume']");
        if (!e) return null;
        const p = e.parentElement, gp = p ? p.parentElement : null;
        return {alt: e.alt,
                cls: (e.className || '').toString(),
                src: (e.currentSrc || e.src || '').slice(-60),
                parent: p ? (p.className || '').toString() : '',
                grand: gp ? (gp.className || '').toString() : ''};
        """
        before_state = driver.execute_script(state_js)
        c.found("點擊前狀態：alt=%s parent=%s"
                % (before_state["alt"], before_state["parent"][:60]))

        W.safe_click(driver, VOLUME, timeout=cfg.T_NORMAL)
        W.settle(1.0)
        c.action("第 1 次點擊")

        mid_state = driver.execute_script(state_js)
        if mid_state is None:
            raise AssertionError("點擊後音量 icon 消失，狀態無法判斷")

        diff = [k for k in before_state if before_state[k] != mid_state[k]]
        if not diff:
            # Phase 4 實測：alt / class / src / 父層 / 祖父層全部沒有變化。
            # 該圖示位於公告列（grandparent = 'flex items-center w-full'，class 帶 mr-2），
            # 是公告的裝飾性喇叭圖示，並非音效開關。
            c.check("點擊前後 alt / class / src / 父層 / 祖父層皆無變化")
            c.note("祖父層 = %r，位於公告跑馬燈列內" % mid_state["grand"][:50])
            c.note("狀態未被改變，無需還原")
            c.skip("ic_volume 為公告列裝飾圖示，非可切換開關（Phase 3 盤點誤判，已更正）")

        c.check("狀態已改變（欄位：%s）" % diff)

        # 還原
        W.safe_click(driver, (By.XPATH, "//img[contains(@alt, 'volume')]"),
                     timeout=cfg.T_NORMAL)
        W.settle(1.0)
        c.action("第 2 次點擊（還原）")

        after_state = driver.execute_script(state_js)
        if after_state is None:
            raise AssertionError("還原後找不到音量 icon，狀態可能未復原")
        still_diff = [k for k in before_state if before_state[k] != after_state[k]]
        if still_diff:
            raise AssertionError("還原失敗，仍有差異欄位：%s" % still_diff)
        c.check("已還原為原始狀態，未留下永久設定變更")
