# -*- coding: utf-8 -*-
"""[L] Subordinate Data 下級資料查詢（/subordinateData）。

進入路徑：大廳 -> TabBar EARN -> Club Stars 的 Detail

Phase 8-A 深度 DOM 探查結果：
    語意元素：button 1、input 1、img 12、a_href 0、select 0、iframe 2
    可互動元素 27

    統計顯示（純文字，無 handler）
        Club Stars / Total Number / Today +N / Yesterday +N / This month +N
    Tier 篩選（div + React onClick，各含 img[alt='ic_member']）
        Tier 1 / Tier 2 / Tier 3
    排序控制（div + React onClick）
        Join Time    初始 img[alt='ic_arrow_down_1']（目前排序欄位）
        Commission   初始 img[alt='ic_up_and_down']（未排序）
        -> icon alt 就是排序狀態標記
    日期選擇（div 內含 img[alt='ic_arrow_down_2']）
        點擊開啟年/月/日滾輪 modal，含 Cancel / Confirm
        -> 只用 Cancel 關閉（實測日期不變）；Confirm 會改變查詢條件，不執行
    搜尋
        div 內含 img[alt='ic_search'] + input[placeholder='Phone Number']
        input: type=text、inputMode=numeric、無 maxLength，非數字會被過濾
    Empty state
        img[alt='img_no_results'] + 文字 "It is empty here."

實測注意事項：
    * input 是 React 受控元件：一次送整串字只會留下 1 碼，
      必須用 W.type_text() 逐字輸入；element.clear() 無效，
      必須用 W.clear_input()（Ctrl+A + DELETE）。
    * 測試帳號為每次新開的訪客帳號，Total Number = 0，
      因此查詢結果一律是 Empty state —— 這是正常狀態，不判 FAIL。

安全限制：
    * 搜尋只使用不可能對應真實會員的測試字串（20 個 9），
      不使用真實會員電話、不查詢特定真實會員資料。
    * 日期只開啟後 Cancel，不 Confirm。
    * 測試結束會把排序、搜尋框、日期都還原成初始狀態並驗證。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

EARN_ICON = (By.CSS_SELECTOR, "img[alt='ic_earn_money']")
CLUB_DETAIL = (By.XPATH, "(//button[normalize-space(.)='Detail'])[1]")
SUB_URL_MARK = "/subordinateData"
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")
MODAL = (By.CSS_SELECTOR, "div[class*='z-[1005]']")

SEARCH_INPUT = (By.CSS_SELECTOR, "input")
SEARCH_ICON = (By.XPATH, "(//div[.//img[@alt='ic_search']])[last()]")
TIPS = (By.XPATH, "//button[.//img[@alt='ic_tips_fill']]")
DATE_CTL = (By.XPATH, "//div[contains(@class,'cursor-pointer')][.//img[@alt='ic_arrow_down_2']]")
CANCEL_BTN = (By.XPATH, "//button[normalize-space(.)='Cancel']")
NO_RESULT = (By.CSS_SELECTOR, "img[alt='img_no_results']")

TIERS = ["Tier 1", "Tier 2", "Tier 3"]
SORTS = ["Join Time", "Commission"]

# 不可能對應任何真實會員的測試字串（20 位數，超過任何國家的號碼長度）
TEST_QUERY = "9" * 20

STATE_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
function ctl(txt) {
  return [...document.querySelectorAll('div')]
    .filter(e => t(e.innerText) === txt && getComputedStyle(e).cursor === 'pointer')
    .pop() || null;
}
function tierEl(name) {
  return [...document.querySelectorAll('div')]
    .filter(e => t(e.innerText).startsWith(name) && getComputedStyle(e).cursor === 'pointer')
    .pop() || null;
}
function statOf(label) {
  const e = [...document.querySelectorAll('div,span,p')]
    .find(x => t(x.innerText).startsWith(label + ' ') || t(x.innerText) === label);
  return e ? t(e.innerText) : null;
}
const inp = document.querySelector('input');
const dateEl = [...document.querySelectorAll('div')]
  .find(x => x.querySelector("img[alt='ic_arrow_down_2']") && getComputedStyle(x).cursor === 'pointer');
const sort = {};
['Join Time', 'Commission'].forEach(n => {
  const e = ctl(n);
  sort[n] = e ? ((e.querySelector('img') || {}).alt || '') : null;
});
const tiers = {};
['Tier 1', 'Tier 2', 'Tier 3'].forEach(n => {
  const e = tierEl(n);
  tiers[n] = e ? {text: t(e.innerText), cls: t(e.className).slice(0, 70)} : null;
});
return {
  url: location.href,
  modal: !!document.querySelector("div[class*='z-[1005]']"),
  no_result: !!document.querySelector("img[alt='img_no_results']"),
  empty_text: /It is empty here/i.test(document.body.innerText),
  input_value: inp ? inp.value : null,
  date_text: dateEl ? t(dateEl.innerText) : null,
  sort: sort,
  tiers: tiers,
  stats: {total: statOf('Total Number'), today: statOf('Today'),
          yesterday: statOf('Yesterday'), month: statOf('This month')},
  rows: document.querySelectorAll("img[alt='ic_coin']").length,
  body: t(document.body.innerText).slice(0, 180)
};
"""


def _tier(name):
    return (By.XPATH, "(//div[starts-with(normalize-space(.),'%s')])[last()]" % name)


def _sort_ctl(name):
    return (By.XPATH, "(//div[normalize-space(.)='%s'][.//img])[last()]" % name)


def _at_sub(driver):
    try:
        return SUB_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _state(driver):
    try:
        return driver.execute_script(STATE_JS) or {}
    except Exception:
        return {}


def _goto_sub(ctx, c=None):
    """大廳 -> EARN -> Club Stars Detail。"""
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_sub(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, EARN_ICON, timeout=cfg.T_NORMAL)
        W.settle(1.4)
        W.safe_click(driver, CLUB_DETAIL, timeout=cfg.T_NORMAL)
        W.settle(1.4)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_sub(driver):
        c.action("已進入 /subordinateData")
    return _at_sub(driver)


def _describe(st):
    return ("sort=%s tiers=%s input=%r date=%r empty=%s"
            % (st.get("sort"),
               dict((k, (v or {}).get("text")) for k, v in (st.get("tiers") or {}).items()),
               st.get("input_value"), st.get("date_text"), st.get("empty_text")))


def _close_modal(ctx):
    """日期 modal 只能用 Cancel 關閉（沒有 ic_close）。Confirm 絕不點。"""
    W = ctx.W
    driver = ctx.driver
    if not W.exists(driver, MODAL, 0):
        return True
    if W.exists(driver, CANCEL_BTN, 0):
        try:
            W.safe_click(driver, CANCEL_BTN, timeout=ctx.config.T_SHORT)
            W.settle(0.9)
        except W.SOFT_EXCEPTIONS:
            pass
    if W.exists(driver, MODAL, 0):
        ctx.P.close_all(driver)
        W.settle(0.6)
    return not W.exists(driver, MODAL, 0)


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("L", "Subordinate Data 下級資料查詢")
    initial = {}

    # ============================================================== L-0
    with ctx.case("L-0", "進入 /subordinateData 並記錄初始狀態") as c:
        if not _goto_sub(ctx, c):
            c.skip("無法進入 /subordinateData")
        c.check("已進入 %s" % driver.current_url)

        data = dom_scan.scan_interactive(driver, "subordinate", settle=0.6)
        path = dom_scan.save(data, cfg.PROBE_DIR, "subordinate_interactive")
        c.check("可互動元素 %d 個（snapshot：%s）" % (data["count"], path))

        initial = _state(driver)
        if not initial.get("sort"):
            raise AssertionError("讀不到排序控制項狀態")
        c.check("初始狀態：%s" % _describe(initial))
        c.note("內容摘要：%s" % initial.get("body", "")[:120])

    # ============================================================== L-1 統計
    with ctx.case("L-1", "統計顯示（Total Number / Today / Yesterday / This month）") as c:
        if not _goto_sub(ctx):
            c.skip("無法進入 /subordinateData")
        st = _state(driver)
        stats = st.get("stats") or {}
        missing = [k for k, v in stats.items() if not v]
        c.found("讀取到統計欄位：%s" % list(stats.keys()))
        for k, v in stats.items():
            c.check("%-10s = %r" % (k, v))
        if missing:
            raise AssertionError("以下統計欄位讀不到：%s" % missing)
        c.note("此區為純顯示文字，無 click handler，僅做唯讀驗證")

    # ============================================================== L-2 ~ L-4 Tier
    for idx, name in enumerate(TIERS, start=2):
        with ctx.case("L-%d" % idx, "Tier 篩選 %s" % name) as c:
            if not _goto_sub(ctx):
                c.skip("無法進入 /subordinateData")
            _close_modal(ctx)

            before = _state(driver)
            tier = (before.get("tiers") or {}).get(name)
            if not tier:
                c.skip("此頁沒有 %s" % name)
            c.found("找到 %s（顯示 %r）" % (name, tier["text"]))

            info = W.probe(driver, _tier(name), timeout=cfg.T_SHORT)
            if not info["clickable"]:
                c.skip("%s 不可點擊（displayed=%s enabled=%s）"
                       % (name, info["displayed"], info["enabled"]))

            W.safe_click(driver, _tier(name), timeout=cfg.T_NORMAL)
            c.action("已點擊 %s" % name)
            W.settle(1.2)
            W.note_toast(driver, c)

            after = _state(driver)
            changed = [k for k in ("tiers", "rows", "no_result", "body", "url")
                       if before.get(k) != after.get(k)]
            if changed:
                c.check("點擊後變化欄位：%s" % changed)
            else:
                # 測試帳號 Total Number = 0，沒有下級可篩選
                c.check("點擊後無可觀察變化 — 本帳號 %s（無下級資料可篩選），屬正常狀態"
                        % (before.get("stats") or {}).get("total"))
            if after.get("empty_text") or after.get("no_result"):
                c.check("維持 Empty state（It is empty here. / img_no_results）")

    # ============================================================== L-5 / L-6 排序
    for idx, name in enumerate(SORTS, start=5):
        with ctx.case("L-%d" % idx, "排序 %s" % name) as c:
            if not _goto_sub(ctx):
                c.skip("無法進入 /subordinateData")
            _close_modal(ctx)

            before = _state(driver)
            if (before.get("sort") or {}).get(name) is None:
                c.skip("此頁沒有 %s 排序控制項" % name)
            c.found("找到 %s（目前 icon = %s）" % (name, before["sort"][name]))
            c.check("排序初始狀態：%s" % before["sort"])

            W.safe_click(driver, _sort_ctl(name), timeout=cfg.T_NORMAL)
            c.action("已點擊 %s" % name)
            W.settle(1.3)
            W.note_toast(driver, c)

            mid = _state(driver)
            if mid.get("sort") == before.get("sort"):
                raise AssertionError("點擊 %s 後排序狀態沒有變化：%s" % (name, mid.get("sort")))
            c.check("排序已變更：%s -> %s" % (before["sort"], mid["sort"]))

            # 還原：再點一次（Join Time 為 toggle；Commission 需切回 Join Time）
            W.safe_click(driver, _sort_ctl(name), timeout=cfg.T_NORMAL)
            W.settle(1.3)
            after = _state(driver)
            if after.get("sort") != before.get("sort"):
                c.action("再點一次未回到初始，改點 Join Time 還原")
                W.safe_click(driver, _sort_ctl("Join Time"), timeout=cfg.T_NORMAL)
                W.settle(1.3)
                after = _state(driver)
            if after.get("sort") != before.get("sort"):
                raise AssertionError("排序未能還原：%s -> %s"
                                     % (before.get("sort"), after.get("sort")))
            c.check("排序已還原為初始狀態：%s" % after["sort"])

    # ============================================================== L-7 日期
    with ctx.case("L-7", "日期選擇器（開啟後 Cancel，不 Confirm）") as c:
        if not _goto_sub(ctx):
            c.skip("無法進入 /subordinateData")
        _close_modal(ctx)

        before = _state(driver)
        info = W.probe(driver, DATE_CTL, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("此頁沒有日期選擇控制項")
        c.found("找到日期控制項（clickable=%s）" % info["clickable"])
        c.check("點擊前日期顯示 = %r" % before.get("date_text"))

        W.safe_click(driver, DATE_CTL, timeout=cfg.T_NORMAL)
        c.action("已點擊日期控制項")
        W.settle(1.4)

        if not W.exists(driver, MODAL, cfg.T_SHORT):
            raise AssertionError("點擊日期後沒有開啟 modal")
        c.check("已開啟日期選擇 modal")

        minfo = P.modal_info(driver)
        if minfo:
            c.note("modal buttons=%s" % (minfo.get("buttons")[:6],))
            c.note("modal 內容：%s" % (minfo.get("text") or "")[:90])
        for b in (minfo or {}).get("buttons", []):
            if b.strip().lower() == "confirm":
                c.check("[L1 不點擊] Confirm 會套用新的查詢日期，本測試不執行")

        data = dom_scan.scan(driver, "subordinate:date", settle=0.6)
        p = dom_scan.save(data, cfg.PROBE_DIR, "subordinate_date")
        c.check("DOM snapshot：%s" % dom_scan.summarize(data))
        c.note("snapshot 檔案：%s" % p)

        if not _close_modal(ctx):
            raise AssertionError("日期 modal 關不掉")
        c.action("已用 Cancel 關閉 modal")

        after = _state(driver)
        if after.get("date_text") != before.get("date_text"):
            raise AssertionError("Cancel 之後日期被改變：%r -> %r"
                                 % (before.get("date_text"), after.get("date_text")))
        c.check("日期未變更，查詢條件維持原狀")

    # ============================================================== L-8 搜尋
    with ctx.case("L-8", "Phone Number 搜尋（測試字串，不查真實會員）") as c:
        if not _goto_sub(ctx):
            c.skip("無法進入 /subordinateData")
        _close_modal(ctx)

        info = W.probe(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("此頁沒有搜尋輸入框")
        attrs = driver.execute_script(
            "const e=document.querySelector('input');"
            "return e?{type:e.type,inputMode:e.inputMode,placeholder:e.placeholder,"
            "maxLength:e.maxLength,readOnly:e.readOnly}:null;")
        c.found("找到搜尋輸入框：%s" % attrs)

        before = _state(driver)
        c.check("輸入前 value=%r，Empty state=%s"
                % (before.get("input_value"), before.get("empty_text")))

        # React 受控元件：必須逐字輸入
        value = W.type_text(driver, SEARCH_INPUT, TEST_QUERY, timeout=cfg.T_NORMAL)
        c.action("已逐字輸入測試字串（%d 位數，不對應任何真實會員）" % len(TEST_QUERY))
        if value != TEST_QUERY:
            raise AssertionError("輸入值不符：預期 %r，實際 %r" % (TEST_QUERY, value))
        c.check("輸入框實際值 = %r（%d 碼）" % (value, len(value)))

        # 觸發查詢
        from selenium.webdriver.common.keys import Keys
        driver.find_element(*SEARCH_INPUT).send_keys(Keys.ENTER)
        W.settle(1.8)
        W.note_toast(driver, c)

        searched = _state(driver)
        if searched.get("no_result") or searched.get("empty_text"):
            c.check("查詢結果為 Empty state（img_no_results / It is empty here.）"
                    " — 本帳號無下級資料，屬正常結果")
        else:
            c.check("查詢結果列數 = %s" % searched.get("rows"))
        c.note("查詢後內容：%s" % searched.get("body", "")[:110])

        # 還原
        cleared = W.clear_input(driver, SEARCH_INPUT, timeout=cfg.T_NORMAL)
        c.action("已清空搜尋框（Ctrl+A + DELETE；element.clear() 對受控元件無效）")
        if cleared:
            raise AssertionError("搜尋框未清空，殘留 %r" % cleared)
        W.settle(1.2)

        after = _state(driver)
        c.check("清空後 value=%r" % after.get("input_value"))
        if after.get("input_value"):
            raise AssertionError("清空後 value 仍為 %r" % after.get("input_value"))
        c.check("已還原為初始查詢狀態")

    # ============================================================== L-9 搜尋 icon
    with ctx.case("L-9", "搜尋 icon（ic_search）") as c:
        if not _goto_sub(ctx):
            c.skip("無法進入 /subordinateData")
        _close_modal(ctx)

        info = W.probe(driver, SEARCH_ICON, timeout=cfg.T_SHORT)
        if not info["found"]:
            c.skip("此頁沒有 ic_search")
        c.found("找到 ic_search（clickable=%s）" % info["clickable"])

        before = _state(driver)
        if not info["clickable"]:
            c.check("不可點擊，僅為輸入框旁的裝飾 icon")
        else:
            W.safe_click(driver, SEARCH_ICON, timeout=cfg.T_NORMAL)
            c.action("已點擊 ic_search")
            W.settle(1.2)
            after = _state(driver)
            changed = [k for k in ("modal", "no_result", "input_value", "body")
                       if before.get(k) != after.get(k)]
            if changed:
                c.check("點擊後變化欄位：%s" % changed)
                _close_modal(ctx)
            else:
                c.check("點擊後無變化（搜尋以輸入框內容即時觸發，icon 不獨立送出查詢）")
        if not _at_sub(driver):
            _goto_sub(ctx)
        c.check("仍在 /subordinateData")

    # ============================================================== L-10 說明 icon
    with ctx.case("L-10", "ic_tips_fill 說明 icon") as c:
        if not _goto_sub(ctx):
            c.skip("無法進入 /subordinateData")
        _close_modal(ctx)

        info = W.probe(driver, TIPS, timeout=cfg.T_SHORT)
        if not info["found"]:
            c.skip("此頁沒有 ic_tips_fill")
        c.found("找到說明 icon（clickable=%s）" % info["clickable"])

        before = _state(driver)
        W.safe_click(driver, TIPS, timeout=cfg.T_NORMAL)
        c.action("已點擊說明 icon")
        W.settle(1.2)
        after = _state(driver)

        if after.get("modal"):
            c.check("開啟說明 modal")
            minfo = P.modal_info(driver)
            if minfo:
                c.note("modal 內容：%s" % (minfo.get("text") or "")[:90])
            _close_modal(ctx)
            c.action("已關閉 modal")
        elif before.get("body") != after.get("body"):
            c.check("頁面內容已變更")
        else:
            c.check("點擊後 DOM 無變化（提示型 icon，可能為 hover 觸發）")

    # ============================================================== L-99
    with ctx.case("L-99", "恢復初始狀態驗證") as c:
        if not _goto_sub(ctx):
            c.skip("無法進入 /subordinateData")
        _close_modal(ctx)

        # 實測行為：開啟日期 modal 會把 Join Time 的排序指示重置為 ic_up_and_down。
        # 這是網站自身的 UI 行為，不是測試殘留，因此收尾時主動還原。
        cur = _state(driver)
        if cur.get("sort") != initial.get("sort"):
            c.action("偵測到排序指示與初始不同，主動還原（點擊 Join Time）")
            for _ in range(3):
                if _state(driver).get("sort") == initial.get("sort"):
                    break
                try:
                    W.safe_click(driver, _sort_ctl("Join Time"), timeout=cfg.T_NORMAL)
                    W.settle(1.2)
                except W.SOFT_EXCEPTIONS:
                    break

        # 仍不一致時重新載入頁面：若重新進入後等於初始狀態，
        # 代表查詢條件並未被持久化，只是前端暫態。
        reloaded = False
        if _state(driver).get("sort") != initial.get("sort"):
            c.action("改以重新進入頁面驗證是否持久化")
            ctx.go_home()
            P.close_all(driver)
            _goto_sub(ctx)
            _close_modal(ctx)
            reloaded = True

        final = _state(driver)
        if reloaded:
            c.check("已重新載入頁面後比對（驗證查詢條件未被持久化）")
        c.check("初始：%s" % _describe(initial))
        c.check("結束：%s" % _describe(final))

        problems = []
        if final.get("sort") != initial.get("sort"):
            problems.append("排序 %s -> %s" % (initial.get("sort"), final.get("sort")))
        if (final.get("input_value") or "") != (initial.get("input_value") or ""):
            problems.append("搜尋框 %r -> %r"
                            % (initial.get("input_value"), final.get("input_value")))
        if final.get("date_text") != initial.get("date_text"):
            problems.append("日期 %r -> %r"
                            % (initial.get("date_text"), final.get("date_text")))
        if final.get("stats") != initial.get("stats"):
            problems.append("統計 %s -> %s" % (initial.get("stats"), final.get("stats")))
        if problems:
            raise AssertionError("未恢復初始狀態：%s" % problems)
        c.check("排序 / 搜尋 / 日期 / 統計皆與初始一致")
        c.note("已知網站行為：開啟日期 modal 會重置 Join Time 的排序指示，"
               "屬前端暫態，重新載入即回到預設排序")

        if W.exists(driver, MODAL, 0):
            raise AssertionError("結束時仍有未關閉的 modal")
        c.check("無殘留 modal")

        P.close_all(driver)
        if W.exists(driver, BACK_ICON, 0):
            try:
                W.safe_click(driver, BACK_ICON, timeout=cfg.T_SHORT)
                W.settle(1.0)
                c.action("使用站內返回 icon")
            except W.SOFT_EXCEPTIONS:
                pass
        ctx.go_home()
        if not ctx.R.at_home(driver):
            raise AssertionError("流程結束後未回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)
