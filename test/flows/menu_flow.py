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

# ---------------------------------------------------------------- Lobby Search
# Phase 10-A 實測：Search 是獨立頁面 /search_game（不是 modal）
#   input  placeholder='Find your favorite game'、type=text、inputMode=text、maxLength=32
#          React handlers: onChange / onInput -> 即時搜尋，不需要按 Enter
#   結果    文字 "Search results for the term “<kw>” are:" + 遊戲卡片（189x265）
#   空結果  文字 "It is empty here."
#   ⚠ img[alt='img_no_results'] 在有結果時也存在於 DOM，
#     因此【不能】用它判斷 Empty state，必須用文字判斷。
SEARCH_URL_MARK = "/search_game"
SEARCH_INPUT = (By.CSS_SELECTOR, "input")
SEARCH_MAXLEN = 32
# 明確不可能命中的測試字串（無底線——實測底線會被輸入框過濾掉）
NO_RESULT_QUERY = "QAAUTOMATIONNORESULT202608"

SEARCH_STATE_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
const body = t(document.body.innerText);
const inp = document.querySelector('input');
const cards = [];
document.querySelectorAll('img').forEach(e => {
  const r = e.getBoundingClientRect();
  if (r.width < 80 || r.height < 110) return;
  if (e.alt === 'img_no_results') return;
  let n = e, title = '';
  for (let i = 0; i < 4 && n; i++) {
    n = n.parentElement;
    if (n) { const x = t(n.innerText); if (x && x.length < 40) { title = x; break; } }
  }
  cards.push({title: title, w: Math.round(r.width), h: Math.round(r.height)});
});
const m = body.match(/Search results for the term\s+[“"]([^”"]*)[”"]/);
return {
  url: location.href,
  value: inp ? inp.value : null,
  has_input: !!inp,
  header: !!m,
  term: m ? m[1] : null,
  cards: cards.slice(0, 20),
  count: cards.length,
  empty: /It is empty here/i.test(body),
  no_result_img: !!document.querySelector("img[alt='img_no_results']"),
  body: body.slice(0, 160)
};
"""

# 從大廳實際可見的遊戲卡片取得安全關鍵字（唯讀，不點擊）
LOBBY_GAME_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
const out = [];
document.querySelectorAll('img').forEach(e => {
  const r = e.getBoundingClientRect();
  if (r.width < 150 || r.height < 200) return;
  let n = e, title = '';
  for (let i = 0; i < 4 && n; i++) {
    n = n.parentElement;
    if (n) { const x = t(n.innerText); if (x && x.length < 30) { title = x; break; } }
  }
  if (title) out.push(title);
});
return [...new Set(out)];
"""


def _search_state(driver):
    try:
        return driver.execute_script(SEARCH_STATE_JS) or {}
    except Exception:
        return {}


def _at_search(driver):
    try:
        return SEARCH_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _open_search(ctx):
    """從大廳開啟 Search 頁。"""
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_search(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    target = SEARCH_BTN if W.exists(driver, SEARCH_BTN, 0) else SEARCH_ICON
    try:
        W.safe_click(driver, target, timeout=cfg.T_NORMAL)
        W.settle(1.4)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    return _at_search(driver)


def _close_search(ctx, c=None):
    """離開 Search 頁回大廳。"""
    W = ctx.W
    driver = ctx.driver
    if W.exists(driver, BACK_ICON, 0):
        try:
            W.safe_click(driver, BACK_ICON, timeout=ctx.config.T_SHORT)
            W.settle(1.2)
            if c is not None:
                c.action("使用站內返回 icon 離開 Search")
        except W.SOFT_EXCEPTIONS:
            pass
    if not ctx.R.at_home(driver):
        ctx.go_home()
    return ctx.R.at_home(driver)


def _lobby_keyword(ctx):
    """唯讀取得一個大廳實際存在的遊戲名稱，作為安全搜尋關鍵字。"""
    driver = ctx.driver
    try:
        titles = driver.execute_script(LOBBY_GAME_JS) or []
    except Exception:
        titles = []
    for title in titles:
        word = title.split()[0] if title.split() else ""
        if 3 <= len(word) <= 20 and word.replace("'", "").isalnum():
            return word, title
    return None, None

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

    # ========================================================= D-13-1 ~ D-13-5
    # Lobby Search 完整 E2E（Phase 10）。Search 本身為 L2 可逆；
    # 搜尋結果中的遊戲一律【只讀驗證、零點擊】，不啟動任何遊戲。
    keyword, full_title = None, None

    with ctx.case("D-13-1", "Search 正常關鍵字（由大廳實際遊戲取得）") as c:
        if not _back_home(ctx, c):
            c.skip("無法回到大廳")
        P.close_all(driver)
        W.settle(0.8)

        keyword, full_title = _lobby_keyword(ctx)
        if not keyword:
            c.skip("大廳讀不到可用的遊戲名稱，無法取得安全關鍵字")
        c.found("由大廳實際遊戲取得關鍵字：%r（完整名稱 %r）" % (keyword, full_title))

        if not _open_search(ctx):
            c.skip("無法開啟 Search 頁")
        c.action("已開啟 Search：%s" % driver.current_url)

        attrs = driver.execute_script(
            "const e=document.querySelector('input');"
            "return e?{type:e.type,inputMode:e.inputMode,placeholder:e.placeholder,"
            "maxLength:e.maxLength}:null;")
        c.check("input 屬性：%s" % attrs)

        value = W.type_text(driver, SEARCH_INPUT, keyword, timeout=cfg.T_NORMAL)
        c.action("已逐字輸入關鍵字（共用 W.type_text）")
        if value != keyword:
            raise AssertionError("輸入值不符：預期 %r，實際 %r" % (keyword, value))
        c.check("input value = %r" % value)

        W.settle(2.0)
        W.note_toast(driver, c)
        st = _search_state(driver)
        if not st.get("header"):
            raise AssertionError("找不到搜尋結果標題（Search results for the term …）")
        c.check("結果標題 term = %r" % st.get("term"))
        if st.get("count", 0) < 1:
            raise AssertionError("關鍵字 %r 沒有任何結果（預期至少 1 筆）" % keyword)
        c.check("結果數量 = %d" % st["count"])
        titles = [x["title"] for x in st.get("cards", [])]
        c.check("結果標題：%s" % titles[:8])
        if not any(keyword.lower() in (t or "").lower() for t in titles):
            raise AssertionError("結果中找不到含關鍵字 %r 的遊戲：%s" % (keyword, titles))
        c.check("至少一筆結果標題含關鍵字，搜尋結果正確")
        c.note("[SAFE] 只讀驗證結果，未點擊任何遊戲卡片")

    with ctx.case("D-13-2", "Search 部分關鍵字與大小寫") as c:
        if not keyword:
            c.skip("沒有可用關鍵字")
        if not _open_search(ctx):
            c.skip("無法開啟 Search 頁")

        partial = keyword[:max(3, len(keyword) // 2)]
        W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        W.type_text(driver, SEARCH_INPUT, partial, timeout=cfg.T_NORMAL)
        W.settle(2.0)
        st_partial = _search_state(driver)
        c.found("部分關鍵字 %r -> 結果 %d 筆" % (partial, st_partial.get("count", 0)))
        if st_partial.get("count", 0) < 1:
            raise AssertionError("部分關鍵字 %r 沒有任何結果" % partial)
        c.check("部分關鍵字可搜尋，結果：%s"
                % [x["title"] for x in st_partial.get("cards", [])][:6])

        upper = keyword.upper()
        W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        W.type_text(driver, SEARCH_INPUT, upper, timeout=cfg.T_NORMAL)
        W.settle(2.0)
        st_upper = _search_state(driver)
        c.check("大寫 %r -> 結果 %d 筆" % (upper, st_upper.get("count", 0)))
        if st_upper.get("count", 0) < 1:
            raise AssertionError("大寫關鍵字 %r 沒有任何結果" % upper)
        c.check("搜尋為大小寫不敏感")

    with ctx.case("D-13-3", "Search Empty State（不存在的關鍵字）") as c:
        if not _open_search(ctx):
            c.skip("無法開啟 Search 頁")

        W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        value = W.type_text(driver, SEARCH_INPUT, NO_RESULT_QUERY, timeout=cfg.T_NORMAL)
        c.action("已輸入不可能命中的測試字串（%d 碼，maxLength=%d）"
                 % (len(NO_RESULT_QUERY), SEARCH_MAXLEN))
        c.check("input value = %r" % value)
        W.settle(2.2)
        W.note_toast(driver, c)

        st = _search_state(driver)
        c.check("結果數量 = %d，Empty 文字 = %s" % (st.get("count", 0), st.get("empty")))
        if st.get("count", 0) != 0:
            raise AssertionError("不存在的關鍵字卻有 %d 筆結果：%s"
                                 % (st["count"], [x["title"] for x in st.get("cards", [])]))
        if not st.get("empty"):
            raise AssertionError("結果為 0 筆但沒有顯示 Empty state（It is empty here.）")
        c.check("正確顯示 Empty state（It is empty here.）— 0 筆結果屬正常，非失敗")
        c.note("img_no_results 在有結果時也存在於 DOM，因此以文字判斷 Empty state")

    with ctx.case("D-13-4", "Search Clear 與結果還原") as c:
        if not _open_search(ctx):
            c.skip("無法開啟 Search 頁")

        before = _search_state(driver)
        if not before.get("value"):
            W.type_text(driver, SEARCH_INPUT, NO_RESULT_QUERY, timeout=cfg.T_NORMAL)
            W.settle(1.5)
            before = _search_state(driver)
        c.found("清除前 value=%r 結果=%d" % (before.get("value"), before.get("count", 0)))

        cleared = W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        c.action("已清空搜尋框（共用 W.clear_input）")
        if cleared:
            raise AssertionError("搜尋框未清空，殘留 %r" % cleared)
        W.settle(1.8)

        after = _search_state(driver)
        c.check("清除後 value=%r" % after.get("value"))
        if after.get("value"):
            raise AssertionError("清除後 value 仍為 %r" % after.get("value"))
        if after.get("header"):
            raise AssertionError("清除後仍顯示搜尋結果標題")
        if after.get("count", 0) != 0:
            raise AssertionError("清除後仍有 %d 筆結果" % after["count"])
        c.check("已回到 Search 預設狀態（無結果標題、無卡片）")
        c.note("預設頁面內容：%s" % (after.get("body") or "")[:60])

    with ctx.case("D-13-5", "Search 結果遊戲只讀驗證 + 關閉 Search") as c:
        if not keyword:
            c.skip("沒有可用關鍵字")
        if not _open_search(ctx):
            c.skip("無法開啟 Search 頁")

        W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        W.type_text(driver, SEARCH_INPUT, keyword, timeout=cfg.T_NORMAL)
        W.settle(2.0)
        st = _search_state(driver)
        if st.get("count", 0) < 1:
            c.skip("此次搜尋沒有結果，無法做結果驗證")
        c.found("結果 %d 筆" % st["count"])

        for card in st.get("cards", [])[:8]:
            c.check("[L1 只讀不點擊] %r %sx%s"
                    % (card.get("title"), card.get("w"), card.get("h")))

        for name in ("Play", "Enter", "Start"):
            pr = W.probe(driver, W.by_button_text(name), timeout=1)
            if pr["found"]:
                c.check("[SAFE-L1] %s 存在但未點擊 displayed=%s enabled=%s"
                        % (name, pr["displayed"], pr["enabled"]))
        c.note("[SAFE-L1] 全程未點擊任何遊戲卡片，未啟動任何遊戲")

        # Recovery：清空 -> 關閉 Search -> 回大廳
        W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        W.settle(1.0)
        residual = _search_state(driver).get("value")
        if residual:
            raise AssertionError("離開前搜尋框仍殘留 %r" % residual)
        c.action("已清空搜尋框")

        if not _close_search(ctx, c):
            raise AssertionError("無法從 Search 頁回到大廳")
        if not ctx.R.strong_anchor_found(driver, timeout=cfg.T_SHORT):
            raise AssertionError("回到大廳後找不到結構性錨點")
        c.check("已回到大廳並命中錨點：%s" % ctx.R.found_anchors(driver)[:3])
        if len(driver.window_handles) != 1:
            raise AssertionError("結束時分頁數不為 1")
        if W.exists(driver, MODAL, 0):
            raise AssertionError("結束時仍有殘留 modal")
        c.check("無殘留 Search 頁 / modal / 額外分頁")

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
