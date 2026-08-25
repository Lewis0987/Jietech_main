# -*- coding: utf-8 -*-
"""[H] Balance details 帳變明細（/record）— 查詢 / 篩選功能。

Phase 6-A 深度 DOM 探查（全頁 0 個 <button>，全是 div + React onClick）：

    上層分頁  div.w-40.h-full...cursor-pointer   Detail / Withdrawal
              -> active 的那個 class 會多一個 'active' token
    篩選列    div.pb-3...cursor-pointer          All / Income / Expense
              -> active 判斷：class 【不含】 'border-transparent'

實測資料（測試帳號為每次新開的訪客帳號）：
    All     -> 1 筆 Register Reward +100.00
    Income  -> 1 筆（同上）
    Expense -> 0 筆，顯示 "It is empty here."
    Withdrawal 分頁 -> 0 筆，顯示 "It is empty here."，且沒有 All/Income/Expense 篩選列

【重要】測試帳號沒有交易資料是正常的。
Empty list 絕對不能判 FAIL；判斷依據是
「篩選是否切換成功 + active 狀態是否正確 + UI 是否正常」。

所有操作都是可逆查詢，測試結束會切回初始狀態（Detail + All）並驗證。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

MINE_ICON = (By.CSS_SELECTOR, "img[alt='ic_user']")
BALANCE_ROW = (By.XPATH, "//button[.//img[@alt='ic_bank']]")
RECORD_URL_MARK = "/record"
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")

TABS = ["Detail", "Withdrawal"]
FILTERS = ["All", "Income", "Expense"]

STATE_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
function pick(name) {
  return [...document.querySelectorAll('div,p,span')].find(
    e => t(e.innerText) === name && getComputedStyle(e).cursor === 'pointer') || null;
}
const out = {tabs: {}, filters: {}};
arguments[0].forEach(n => {
  const e = pick(n);
  // Phase 9-A 實測：active 分頁的標記是內部的 img[alt='active']，
  // 不是 class token（舊版用 class 判斷從未成立，active 一直是 None）。
  out.tabs[n] = e ? {cls: t(e.className),
                     active: !!e.querySelector("img[alt='active']")} : null;
});
arguments[1].forEach(n => {
  const e = pick(n);
  // 篩選列：active 的那個沒有 border-transparent
  out.filters[n] = e ? {cls: t(e.className),
                        active: !t(e.className).includes('border-transparent')} : null;
});
out.rows = document.querySelectorAll("img[alt='ic_coin']").length;
out.empty = /It is empty here/i.test(document.body.innerText);
out.no_result_img = !!document.querySelector("img[alt='img_no_results']");
// 各分頁的欄位標題（Detail 與 Withdrawal Record 欄位不同）
const bodyText = document.body.innerText || '';
out.columns = ['Type', 'Change', 'Balance', 'Time & Order Number', 'Request Amount', 'State']
  .filter(c => bodyText.indexOf(c) >= 0);
// /record 目前沒有 input / date / sort / pagination，一併記錄以便未來變更時發現
out.controls = {
  inputs: document.querySelectorAll('input').length,
  buttons: document.querySelectorAll('button').length,
  selects: document.querySelectorAll('select').length,
  date_like: document.querySelectorAll("img[alt*='arrow_down'],img[alt*='calendar']").length,
  sort_like: document.querySelectorAll("img[alt*='up_and_down']").length,
  pager_like: [...document.querySelectorAll('div,span')].filter(e => {
      const x = t(e.innerText);
      return /^(Next|Prev|Previous|Load more|More)$/i.test(x);
    }).length
};
out.body = t(document.body.innerText).slice(0, 160);
return out;
"""


def _el(name):
    return (By.XPATH, "//div[normalize-space(text())='%s']" % name)


def _at_record(driver):
    try:
        return RECORD_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _state(driver):
    try:
        return driver.execute_script(STATE_JS, TABS, FILTERS) or {}
    except Exception:
        return {}


def _active_tab(state):
    for n, v in (state.get("tabs") or {}).items():
        if v and v.get("active"):
            return n
    return None


def _active_filter(state):
    for n, v in (state.get("filters") or {}).items():
        if v and v.get("active"):
            return n
    return None


def _goto_record(ctx, c=None):
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_record(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, MINE_ICON, timeout=cfg.T_NORMAL)
        W.settle(1.2)
        W.safe_click(driver, BALANCE_ROW, timeout=cfg.T_NORMAL)
        W.settle(1.2)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_record(driver):
        c.action("已進入 /record")
    return _at_record(driver)


def _describe(state):
    return ("rows=%s empty=%s tab=%s filter=%s"
            % (state.get("rows"), state.get("empty"),
               _active_tab(state), _active_filter(state)))


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("H", "Balance details 查詢 / 篩選")
    initial = {}

    # ============================================================== H-0
    with ctx.case("H-0", "進入 /record 並記錄初始狀態") as c:
        if not _goto_record(ctx, c):
            c.skip("無法進入 /record")
        c.check("已進入 %s" % driver.current_url)

        initial = _state(driver)
        if not initial.get("tabs"):
            raise AssertionError("讀不到分頁狀態")
        c.check("初始狀態：%s" % _describe(initial))
        c.note("內容摘要：%s" % initial.get("body", "")[:110])

        data = dom_scan.scan_interactive(driver, "record", settle=0.5)
        path = dom_scan.save(data, cfg.PROBE_DIR, "record_interactive")
        c.check("可互動元素 %d 個（snapshot：%s）" % (data["count"], path))

        if _active_tab(initial) is None:
            c.note("初始沒有任何分頁帶 active token（將以切換前後差異判定）")

    # ============================================================== H-1 ~ H-3 篩選
    for idx, name in enumerate(FILTERS, start=1):
        with ctx.case("H-%d" % idx, "篩選 %s" % name) as c:
            if not _goto_record(ctx):
                c.skip("無法進入 /record")

            before = _state(driver)
            if not (before.get("filters") or {}).get(name):
                c.skip("目前分頁沒有 %s 篩選（例如 Withdrawal 分頁）" % name)
            already = (_active_filter(before) == name)
            c.found("找到篩選 %s（目前 active = %s）" % (name, _active_filter(before)))

            W.safe_click(driver, _el(name), timeout=cfg.T_NORMAL)
            c.action("已點擊 %s" % name)
            W.settle(1.2)
            W.note_toast(driver, c)

            after = _state(driver)
            if _active_filter(after) != name:
                raise AssertionError("點擊 %s 後 active 篩選是 %s"
                                     % (name, _active_filter(after)))
            if already:
                c.check("原本就是 active，點擊後仍維持 active（符合預期）")
            else:
                c.check("active 已切換到 %s" % name)

            # Empty 或有資料都算正常，只記錄不判斷
            if after.get("empty"):
                c.check("查詢結果為 Empty state（It is empty here.）— 測試帳號無此類資料，正常")
            else:
                c.check("查詢結果有 %s 筆資料" % after.get("rows"))
            c.note("內容摘要：%s" % after.get("body", "")[:110])

    # ============================================================== H-4 Withdrawal 分頁
    with ctx.case("H-4", "分頁 Withdrawal Record Tab（交易紀錄查詢，非提款功能）") as c:
        if not _goto_record(ctx):
            c.skip("無法進入 /record")
        before = _state(driver)
        if not (before.get("tabs") or {}).get("Withdrawal"):
            c.skip("找不到 Withdrawal 分頁")
        c.found("找到 Withdrawal 分頁（目前 active = %s）" % _active_tab(before))

        W.safe_click(driver, _el("Withdrawal"), timeout=cfg.T_NORMAL)
        c.action("已點擊 Withdrawal")
        W.settle(1.5)
        W.note_toast(driver, c)

        after = _state(driver)
        if _active_tab(after) != "Withdrawal":
            raise AssertionError("點擊後 active 分頁是 %s（預期 Withdrawal）"
                                 % _active_tab(after))
        c.check("active 分頁已切換為 Withdrawal Record Tab（img[alt='active'] 標記）")

        cols = after.get("columns") or []
        c.check("此分頁欄位標題：%s" % cols)
        if not any(x in cols for x in ("Time & Order Number", "Request Amount", "State")):
            raise AssertionError("Withdrawal Record Tab 沒有預期的欄位標題：%s" % cols)
        if (after.get("filters") or {}).get("All"):
            c.note("此分頁仍有 All/Income/Expense 篩選列")
        else:
            c.check("此分頁沒有 All/Income/Expense 篩選列（版面與 Detail 不同）")

        if after.get("empty"):
            c.check("查詢結果為 Empty state（It is empty here.，img_no_results=%s）"
                    "— 測試帳號無提款紀錄，屬正常" % after.get("no_result_img"))
        else:
            c.check("Withdrawal Record Tab 有 %s 筆資料" % after.get("rows"))
        c.note("此為交易紀錄查詢頁籤（L2 可逆），與 Safety Flow E-2 的提款入口無關")
        c.note("內容摘要：%s" % after.get("body", "")[:110])

    # ============================================================== H-5 Detail 分頁
    with ctx.case("H-5", "分頁 Detail Record Tab（切回）") as c:
        if not _goto_record(ctx):
            c.skip("無法進入 /record")
        before = _state(driver)
        if not (before.get("tabs") or {}).get("Detail"):
            c.skip("找不到 Detail 分頁")
        c.found("找到 Detail 分頁（目前 active = %s）" % _active_tab(before))

        W.safe_click(driver, _el("Detail"), timeout=cfg.T_NORMAL)
        c.action("已點擊 Detail")
        W.settle(1.5)

        after = _state(driver)
        if _active_tab(after) != "Detail":
            raise AssertionError("切回後 active 分頁是 %s（預期 Detail）"
                                 % _active_tab(after))
        c.check("active 分頁已切回 Detail Record Tab")
        if not (after.get("filters") or {}).get("All"):
            raise AssertionError("切回 Detail 後找不到 All/Income/Expense 篩選列")
        c.check("篩選列重新出現")
        cols = after.get("columns") or []
        c.check("此分頁欄位標題：%s" % cols)
        if not any(x in cols for x in ("Type", "Change", "Balance")):
            raise AssertionError("Detail Record Tab 沒有預期的欄位標題：%s" % cols)
        c.check("目前狀態：%s" % _describe(after))

    # ============================================================== H-6
    with ctx.case("H-6", "查詢控制項覆蓋盤點（date / search / sort / pagination）") as c:
        if not _goto_record(ctx):
            c.skip("無法進入 /record")
        st = _state(driver)
        ctrl = st.get("controls") or {}
        c.found("目前 /record 的控制項統計：%s" % ctrl)

        missing = []
        if not ctrl.get("inputs"):
            missing.append("搜尋 input")
        if not ctrl.get("date_like"):
            missing.append("日期選擇")
        if not ctrl.get("sort_like"):
            missing.append("排序")
        if not ctrl.get("pager_like"):
            missing.append("分頁 / Load more")

        for m in missing:
            c.check("[Not Applicable] 此頁目前沒有%s控制項，因此不建立對應 Case" % m)
        if not missing:
            c.note("偵測到新的查詢控制項，需要補測試：%s" % ctrl)
        c.check("已涵蓋的查詢控制項：Detail / Withdrawal Record 分頁 + "
                "All / Income / Expense 篩選")
        c.note("本 case 用來偵測網站日後新增查詢控制項；"
               "若 inputs / date / sort / pagination 由 0 變為非 0 即需補測")

    # ============================================================== H-99
    with ctx.case("H-99", "恢復初始狀態驗證") as c:
        if not _goto_record(ctx):
            c.skip("無法進入 /record")

        # 切回初始篩選
        target = _active_filter(initial) or "All"
        cur = _state(driver)
        if _active_filter(cur) != target and (cur.get("filters") or {}).get(target):
            W.safe_click(driver, _el(target), timeout=cfg.T_NORMAL)
            c.action("已切回初始篩選 %s" % target)
            W.settle(1.2)

        final = _state(driver)
        c.check("初始：%s" % _describe(initial))
        c.check("結束：%s" % _describe(final))

        if _active_filter(final) != _active_filter(initial):
            raise AssertionError("篩選未恢復：%s -> %s"
                                 % (_active_filter(initial), _active_filter(final)))
        if final.get("rows") != initial.get("rows") or final.get("empty") != initial.get("empty"):
            raise AssertionError("列表狀態未恢復：rows %s->%s empty %s->%s"
                                 % (initial.get("rows"), final.get("rows"),
                                    initial.get("empty"), final.get("empty")))
        if _active_tab(final) != _active_tab(initial):
            raise AssertionError("分頁未恢復：%s -> %s"
                                 % (_active_tab(initial), _active_tab(final)))
        if final.get("columns") != initial.get("columns"):
            raise AssertionError("欄位標題未恢復：%s -> %s"
                                 % (initial.get("columns"), final.get("columns")))
        c.check("分頁 / 篩選 / 欄位 / 列表狀態皆已恢復初始")

        ctx.go_home()
        c.check("已回到大廳：%s" % driver.current_url)
