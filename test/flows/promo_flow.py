# -*- coding: utf-8 -*-
"""[I] PROMO 活動頁（/activity）。

Phase 6-A 深度 DOM 探查結果：
    /activity 全頁 0 個 <button>、0 個 <a href>，活動卡片是 div + React onClick。

    卡片結構：
        div.grid.gap-4.mt-2                              <- 卡片容器 grid
          └─ div.relative.flex.flex-col.justify-center.rounded-lg.bgi-border-...  <- 卡片
               └─ div.w-full.text-base.font-medium.py-[15px].pl-3.box-border.absolute  <- 標題列
                  （cursor:pointer、z-index:10、高度 54）

Selector 原則：用結構化 class（`py-[15px]` + `pl-3` 的標題列）+ 標題文字定位，
不使用 blob URL、MD5 圖片檔名或動態 CDN URL——活動每天會換圖，
但卡片結構與標題文字是穩定的。

【Phase 6-A 已確認的顯示異常】
    卡片容器高度為 0（與首頁 Banner 相同的塌陷型態），
    10 張活動卡片的標題列以每 16px 的間距互相重疊堆疊，
    document.elementFromPoint 顯示只有最後一張是 topmost，
    其餘 9 張被覆蓋，使用者實際點不到。
    因此 I-00 會 FAIL，被覆蓋的卡片 SKIP 並附上實測證據。

安全分類：進入活動頁後若出現 Claim / Redeem / Submit / SPIN / Deposit，
一律只驗證不點擊。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

PROMO_ICON = (By.CSS_SELECTOR, "img[alt='ic_activity']")
ACTIVITY_URL_MARK = "/activity"
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")
MODAL = (By.CSS_SELECTOR, "div[class*='z-[1005]']")
TAKEN_DOWN = (By.XPATH, '//div[contains(text(), "This game has been taken down")]')

# 只驗證不點擊
DESTRUCTIVE = [
    ("Claim", (By.XPATH, "//button[contains(., 'Claim')]")),
    ("Redeem", (By.XPATH, "//button[contains(., 'Redeem')]")),
    ("Submit", (By.XPATH, "//button[contains(., 'Submit')]")),
    ("Confirm", (By.XPATH, "//button[contains(., 'Confirm')]")),
    ("SPIN", (By.XPATH, "//span[contains(text(), 'SPIN')]")),
    ("Deposit", (By.XPATH, "//button[contains(., 'Deposit')]")),
]

MAX_CARDS = 20

# 盤點所有活動卡片標題列，並判斷是否被覆蓋
SURVEY_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
function reactClick(el) {
  for (const k in el) {
    if (k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$')) {
      const p = el[k];
      if (p && (typeof p.onClick === 'function' || typeof p.onPointerDown === 'function')) return true;
    }
  }
  return false;
}
function handlerNear(el) {
  // 標題列本身、卡片容器、再上一層，任一有 click handler 就算可觸發
  let n = el;
  for (let i = 0; i < 3 && n; i++) { if (reactClick(n)) return true; n = n.parentElement; }
  return false;
}
const titles = [...document.querySelectorAll('div')].filter(e => {
  const c = t(e.className);
  return c.includes('py-[15px]') && c.includes('pl-3') && t(e.innerText);
});
const grid = document.querySelector('div.grid.gap-4');
const cards = grid ? [...grid.children] : [];
const h = e => Math.round(e.getBoundingClientRect().height);
return {
  grid_h: grid ? h(grid) : -1,
  card_count: cards.length,
  max_card_h: cards.length ? Math.max.apply(null, cards.map(h)) : -1,
  titles: titles.map((e, i) => {
    const r = e.getBoundingClientRect();
    const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
    let top = null;
    try { top = document.elementFromPoint(cx, cy); } catch (err) {}
    return {
      i: i,
      text: t(e.innerText).slice(0, 60),
      rect: {x: Math.round(r.x), y: Math.round(r.y),
             w: Math.round(r.width), h: Math.round(r.height)},
      zIndex: getComputedStyle(e).zIndex,
      cursor: getComputedStyle(e).cursor,
      topmost: !!(top && (top === e || e.contains(top))),
      has_handler: handlerNear(e),
      card_h: e.parentElement ? Math.round(e.parentElement.getBoundingClientRect().height) : -1,
      covered_by: top ? t(top.innerText).slice(0, 40) : null
    };
  })
};
"""


def _at_activity(driver):
    try:
        return ACTIVITY_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _goto_activity(ctx, c=None):
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_activity(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, PROMO_ICON, timeout=cfg.T_NORMAL)
        W.settle(1.5)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_activity(driver):
        c.action("已進入 /activity")
    return _at_activity(driver)


def _survey(driver):
    try:
        return driver.execute_script(SURVEY_JS) or {}
    except Exception:
        return {}


def _title_locator(text):
    """以標題文字 + 結構化 class 定位（不依賴圖片 / CDN URL）。"""
    safe = text.replace('"', '')
    return (By.XPATH,
            "//div[contains(@class,'py-[15px]') and contains(@class,'pl-3')]"
            "[normalize-space(.)=\"%s\"]" % safe)


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("I", "PROMO 活動頁")
    titles = []

    # ============================================================== I-00
    with ctx.case("I-00", "活動清單盤點與可視性") as c:
        if not _goto_activity(ctx, c):
            c.skip("無法進入 /activity")
        c.found("已進入 %s" % driver.current_url)

        data = dom_scan.scan_interactive(driver, "activity", settle=0.6)
        path = dom_scan.save(data, cfg.PROBE_DIR, "activity_interactive")
        c.check("可互動元素 %d 個（snapshot：%s）" % (data["count"], path))

        survey = _survey(driver)
        titles = survey.get("titles", [])[:MAX_CARDS]
        if not titles:
            c.skip("/activity 沒有任何活動卡片")

        c.check("活動卡片標題列 %d 個；grid 高度=%spx，卡片數=%s，卡片最大高度=%spx"
                % (len(titles), survey.get("grid_h"), survey.get("card_count"),
                   survey.get("max_card_h")))
        for t in titles:
            c.note("[%d] %r y=%s h=%s topmost=%s%s"
                   % (t["i"], t["text"][:40], t["rect"]["y"], t["rect"]["h"],
                      t["topmost"],
                      ("，被 %r 覆蓋" % t["covered_by"][:24]) if not t["topmost"] else ""))

        reachable = [t for t in titles if t["topmost"]]
        wired = [t for t in titles if t.get("has_handler")]
        c.check("最上層（沒被覆蓋）的活動：%d / %d" % (len(reachable), len(titles)))
        c.check("帶有 click handler 的活動：%d / %d" % (len(wired), len(titles)))

        if int(survey.get("max_card_h", -1)) == 0 or not wired:
            raise AssertionError(
                "【已確認現象】/activity 共 %d 張活動卡片。"
                "(1) 卡片容器渲染高度為 0，標題列以 16px 間距互相重疊，"
                "經 document.elementFromPoint 驗證只有 %d 張是最上層、其餘 %d 張被覆蓋；"
                "(2) 逐一檢查標題列、卡片容器與其上一層，%d / %d 張帶有 click handler，"
                "亦即卡片只有 cursor:pointer 樣式而沒有實際綁定點擊事件。"
                "使用者無法開啟任何活動。"
                "【疑似原因】與首頁 Banner 相同的版面塌陷型態（卡片背景圖未撐開容器），"
                "且活動卡片未綁定點擊事件——尚未經前端修改前後驗證，僅為推測。"
                % (len(titles), len(reachable), len(titles) - len(reachable),
                   len(wired), len(titles)))

    if not titles:
        with ctx.case("I-99", "PROMO 流程收尾") as c:
            c.skip("沒有可測試的活動")
        return

    # ============================================================== I-01 ~ I-NN
    for t in titles:
        case_id = "I-%02d" % (t["i"] + 1)
        label = t["text"][:34] or "(無標題)"

        with ctx.case(case_id, "活動 %s" % label) as c:
            if not _goto_activity(ctx):
                c.skip("無法進入 /activity")
            P.close_all(driver)
            W.settle(0.5)

            cur = _survey(driver)
            match = [x for x in cur.get("titles", []) if x["text"] == t["text"]]
            if not match:
                c.skip("本次載入沒有這個活動（活動清單會變動）")
            item = match[0]

            c.found("locator=標題列 class 含 py-[15px]+pl-3，文字=%r" % label)
            c.check("位置 y=%s h=%s z=%s cursor=%s"
                    % (item["rect"]["y"], item["rect"]["h"],
                       item["zIndex"], item["cursor"]))

            c.check("卡片容器高度 = %spx；標題列/卡片/上層是否帶 click handler = %s"
                    % (item.get("card_h"), item.get("has_handler")))

            if not item["topmost"]:
                c.check("document.elementFromPoint 顯示此處最上層是 %r"
                        % (item["covered_by"] or "")[:30])
                c.skip("被其他活動卡片覆蓋，使用者實際點不到（見 I-00 的塌陷問題）")

            if not item.get("has_handler"):
                c.skip("卡片只有 cursor:pointer 樣式，標題列 / 卡片容器 / 上層皆無 "
                       "React onClick handler，點擊不會有任何反應（見 I-00）")

            info = W.probe(driver, _title_locator(item["text"]), timeout=cfg.T_SHORT)
            if not info["clickable"]:
                c.skip("標題列不可點擊（displayed=%s enabled=%s）"
                       % (info["displayed"], info["enabled"]))

            before_url = driver.current_url
            handles_before = len(driver.window_handles)
            W.safe_click(driver, _title_locator(item["text"]), timeout=cfg.T_NORMAL)
            c.action("已點擊活動卡片")
            W.settle(1.5)
            W.wait_ready(driver, timeout=cfg.T_NORMAL)
            W.note_toast(driver, c)

            # --- C. 外部網站：立刻關閉，不進入 ---
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
                c.check("[L1] 此活動開啟外部分頁 %s，已立即關閉，未進入外部服務" % urls)
                ctx.go_home()
                return_ok = _goto_activity(ctx)
                c.check("已回到 /activity：%s" % return_ok)
                continue

            # --- D. 活動下架 ---
            if W.exists(driver, TAKEN_DOWN, cfg.T_SHORT):
                c.note("偵測到 This game has been taken down")
                ctx.go_home()
                _goto_activity(ctx)
                c.skip("活動已下架")

            # --- A/B. 站內頁面 或 Modal ---
            if W.exists(driver, MODAL, cfg.T_SHORT):
                c.check("開啟 Modal")
                minfo = P.modal_info(driver)
                if minfo:
                    c.note("modal imgs=%s buttons=%s"
                           % (minfo.get("imgs")[:5], minfo.get("buttons")[:6]))
                data = dom_scan.scan(driver, "promo:%s" % label, settle=0.6)
                p = dom_scan.save(data, cfg.PROBE_DIR, "promo_modal")
                c.check("DOM snapshot：%s" % dom_scan.summarize(data))
                c.note("snapshot 檔案：%s" % p)
            elif driver.current_url != before_url:
                c.check("進入站內頁面：%s" % driver.current_url)
                data = dom_scan.scan(driver, "promo:%s" % label, settle=0.6)
                p = dom_scan.save(data, cfg.PROBE_DIR, "promo_page")
                c.check("DOM snapshot：%s" % dom_scan.summarize(data))
                c.note("snapshot 檔案：%s" % p)
            else:
                raise AssertionError("點擊活動後 URL 未變、也沒有 modal")

            # --- E. 破壞性元素：只驗證不點擊 ---
            for name, loc in DESTRUCTIVE:
                pr = W.probe(driver, loc, timeout=1)
                if pr["found"]:
                    c.check("[L1 只驗證不點擊] %s displayed=%s enabled=%s clickable=%s"
                            % (name, pr["displayed"], pr["enabled"], pr["clickable"]))

            # --- Recovery ---
            P.close_all(driver)
            if W.exists(driver, BACK_ICON, 0):
                try:
                    W.safe_click(driver, BACK_ICON, timeout=cfg.T_SHORT)
                    W.settle(1.0)
                    c.action("使用站內返回 icon")
                except W.SOFT_EXCEPTIONS:
                    pass
            if not _at_activity(driver):
                ctx.go_home()
                _goto_activity(ctx)
            if not _at_activity(driver):
                raise AssertionError("無法回到 /activity（目前 %s）" % driver.current_url)
            c.check("已回到 /activity")

    # ============================================================== I-99
    with ctx.case("I-99", "PROMO 流程收尾") as c:
        c.check("共處理 %d 個活動 case" % len(titles))
        c.check("未執行任何 Claim / Redeem / Submit / SPIN / Deposit")
        ctx.go_home()
        if not ctx.R.at_home(driver):
            raise AssertionError("PROMO 流程結束後未回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)
