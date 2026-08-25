# -*- coding: utf-8 -*-
"""[J] Task Center 任務中心（/task_center）— 安全分類驗證。

Phase 6-E 唯讀安全探查結論：

    Claim all ×1
        領獎，不可逆 -> L1，絕不點擊。

    Go ×6
        對應 6 個「Wager 1000」任務，限定分類分別為：
            slot / live / original / game / fishing / sport
        嘗試從 React fiber 讀取 onClick 原始碼以判斷目的地，
        但程式碼已被 minify 成 `h=>{d(h)}`，**無法唯讀確認導向何處**。

        依安全原則「目的不明維持 L1」，6 個 Go 全部保持 L1：
          * 任務本身是「投注 1000」的流水任務
          * 無法排除 Go 會深入連結到遊戲內
          * 不為了提高 Coverage 而強行點擊

因此本 flow 全程 **不點擊任何任務按鈕**，
只做導航進入 /task_center + 逐一 L1 驗證 + 記錄每個 Go 的任務內容，
作為之後前端確認導向後升級 L2 的依據。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

MINE_ICON = (By.CSS_SELECTOR, "img[alt='ic_user']")
MISSION_ROW = (By.XPATH, "//button[.//img[@alt='ic_mission']]")
TASK_URL_MARK = "/task_center"
CLAIM_ALL = (By.XPATH, "//button[contains(., 'Claim all')]")

# 逐一取出每個 Go 按鈕與其任務描述（唯讀）
GO_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
const gos = [...document.querySelectorAll('button')].filter(b => t(b.innerText) === 'Go');
return gos.map((b, i) => {
  const r = b.getBoundingClientRect();
  let src = '';
  for (const k in b) {
    if (k.startsWith('__reactProps$')) {
      const p = b[k];
      if (p && typeof p.onClick === 'function') src = p.onClick.toString().slice(0, 120);
    }
  }
  let card = b, desc = '';
  for (let j = 0; j < 5 && card; j++) {
    card = card.parentElement;
    if (card && t(card.innerText).length > 20) { desc = t(card.innerText).slice(0, 90); break; }
  }
  let cat = '';
  const m = desc.match(/Restricted to:\s*([a-z]+)/i);
  if (m) cat = m[1];
  return {i: i, desc: desc, category: cat, onclick_src: src,
          cls: t(b.className).slice(0, 60),
          disabled: !!b.disabled,
          cursor: getComputedStyle(b).cursor,
          rect: {y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}};
});
"""


def _at_task(driver):
    try:
        return TASK_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _goto_task(ctx, c=None):
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_task(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, MINE_ICON, timeout=cfg.T_NORMAL)
        W.settle(1.2)
        W.safe_click(driver, MISSION_ROW, timeout=cfg.T_NORMAL)
        W.settle(1.2)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_task(driver):
        c.action("已進入 /task_center")
    return _at_task(driver)


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("J", "Task Center（全程只驗證不點擊）")
    gos = []

    # ============================================================== J-0
    with ctx.case("J-0", "進入 /task_center") as c:
        if not _goto_task(ctx, c):
            c.skip("無法進入 /task_center")
        c.check("已進入 %s" % driver.current_url)

        data = dom_scan.scan_interactive(driver, "task_center", settle=0.6)
        path = dom_scan.save(data, cfg.PROBE_DIR, "task_center_interactive")
        c.check("可互動元素 %d 個（snapshot：%s）" % (data["count"], path))

        try:
            gos = driver.execute_script(GO_JS) or []
        except Exception:
            gos = []
        c.check("偵測到 Go 按鈕 %d 個" % len(gos))

    # ============================================================== J-1 Claim all
    with ctx.case("J-1", "Claim all（L1 絕不點擊）") as c:
        if not _goto_task(ctx):
            c.skip("無法進入 /task_center")
        info = W.probe(driver, CLAIM_ALL, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("此頁沒有 Claim all")
        c.found("Claim all 存在：//button[contains(., 'Claim all')]")
        c.check("displayed = %s" % info["displayed"])
        c.check("enabled   = %s" % info["enabled"])
        c.check("clickable = %s" % info["clickable"])
        cursor = driver.execute_script(
            "const b=[...document.querySelectorAll('button')]"
            ".find(x=>x.innerText.trim().startsWith('Claim all'));"
            "return b?getComputedStyle(b).cursor:null;")
        c.check("cursor = %s%s" % (cursor,
                                   "（default，目前無可領取任務）" if cursor == "default" else ""))
        c.note("[SAFE-L1] 領獎為不可逆操作，本 case 未執行任何點擊")

    # ============================================================== J-2 ~ J-N
    if not gos:
        with ctx.case("J-2", "Go 按鈕安全分類") as c:
            c.skip("此頁沒有 Go 按鈕")
    else:
        for g in gos:
            case_id = "J-%d" % (g["i"] + 2)
            cat = g["category"] or "?"
            with ctx.case(case_id, "Go #%d（限定分類 %s，L1 只分類）" % (g["i"] + 1, cat)) as c:
                if not _goto_task(ctx):
                    c.skip("無法進入 /task_center")

                cur = driver.execute_script(GO_JS) or []
                match = [x for x in cur if x["i"] == g["i"]]
                if not match:
                    c.skip("本次載入沒有這個 Go 按鈕（任務清單會變動）")
                item = match[0]

                c.found("Go #%d 存在（y=%s, %sx%s）"
                        % (item["i"] + 1, item["rect"]["y"],
                           item["rect"]["w"], item["rect"]["h"]))
                c.check("任務內容：%s" % item["desc"][:80])
                c.check("限定分類：%s" % (item["category"] or "(無法解析)"))
                c.check("disabled = %s / cursor = %s" % (item["disabled"], item["cursor"]))
                c.check("onClick 原始碼：%r（已 minify，無法唯讀判斷導向）"
                        % (item["onclick_src"] or "(讀不到)"))

                c.note("[SAFE-L1] 安全分類 = 目的不明。"
                       "任務為『投注 1000』流水任務，無法排除點擊後深入連結至遊戲內，"
                       "依原則維持 L1，未點擊。")

    # ============================================================== J-99
    with ctx.case("J-99", "Task Center 收尾") as c:
        c.check("Claim all 零點擊")
        c.check("Go x%d 全部維持 L1，零點擊" % len(gos))
        ctx.go_home()
        if not ctx.R.at_home(driver):
            raise AssertionError("Task 流程結束後未回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)
