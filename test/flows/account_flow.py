# -*- coding: utf-8 -*-
"""[G] Account 個人資料（/account）。

Phase 6-A 深度 DOM 探查結果（React SPA，全頁 0 個 <button>）：
每一列的結構固定為

    div.flex.items-center.px-5.py-3...          <- 列容器（無 handler）
      ├─ div  文字 = 欄位名稱                    <- label（無 handler）
      └─ div.flex.items-center.bgi-text-[...]   <- 值 + 箭頭/複製 icon（React onClick）

因此 locator 一律為：
    //div[normalize-space(text())='<欄位名稱>']/following-sibling::div[1]

Phase 6-A 實測各列點擊行為（探查期間暱稱全程未變）：
    Avatar               -> 開 modal（頭像選擇器）        L2 只開/關，不選頭像
    Player ID            -> 無任何變化（純顯示）           唯讀
    Nickname             -> 開 modal，input + Save        L2 只開/關，不輸入不 Save
    Gender               -> 開 modal（性別選擇器）         L2 只開/關，不選
    My invitation code   -> 值元素帶 onClick（複製）       L1 不點
    Bind phone number    -> 開 modal，含 Send / Confirm   L1 不點
    Login password       -> 開 modal，含 Send / Complete  L1 不點
    Bind invitation code -> 開 modal，含 Cancel / Confirm L1 不點

Bind / Login password 之所以維持 L1（即使「開啟」本身可逆）：
modal 內含 **Send**（發送簡訊驗證碼）按鈕，屬於對外動作，
不在測試範圍內冒險開啟。

G-99 會比對測試前後的所有欄位值，確認自動化沒有改到任何帳號資料。
"""

from selenium.webdriver.common.by import By

from common import dom_scan

MINE_ICON = (By.CSS_SELECTOR, "img[alt='ic_user']")
MY_INFO_ROW = (By.XPATH, "//button[.//img[@alt='ic_info']]")
ACCOUNT_URL_MARK = "/account"
MODAL = (By.CSS_SELECTOR, "div[class*='z-[1005]']")
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")
# Avatar 這類「全螢幕型 modal」沒有 ic_close，關閉鈕是 modal 內部的返回 icon。
# 必須限定在 modal 之內，否則會點到被 modal 蓋住的頁面返回鈕，導致誤導航。
MODAL_BACK = (By.XPATH,
              "//div[contains(@class,'z-[1005]')]//img[contains(@alt,'ic_back_header')]")

# 需要記錄 / 比對的欄位
FIELDS = ["Player ID", "Nickname", "Gender", "My invitation code",
          "Bind phone number", "Login password", "Bind invitation code"]

# L2：點擊只會開 modal，不會立即改資料
REVERSIBLE = [
    ("G-1", "Avatar 頭像", "Avatar", "avatar"),
    ("G-2", "Nickname 暱稱", "Nickname", "nickname"),
    ("G-3", "Gender 性別", "Gender", "gender"),
]

# L1：只驗證不點擊
L1_ROWS = [
    ("G-6", "Bind phone number 綁定手機", "Bind phone number",
     "modal 內含 Send（發送簡訊驗證碼）"),
    ("G-7", "Login password 登入密碼", "Login password",
     "modal 內含 Send / Complete（修改密碼）"),
    ("G-8", "Bind invitation code 綁定邀請碼", "Bind invitation code",
     "modal 內含 Confirm（綁定為不可逆）"),
]

# 每個列容器（px-5 py-3 border-b）固定是兩個子元素：[label, value]。
# 直接走列容器比用文字找 label 再取 nextElementSibling 可靠——
# 後者在 value 為空字串（Avatar / Gender）時會抓到下一列，造成誤判。
READ_FIELDS_JS = r"""
const t = s => (s || '').toString().replace(/\s+/g, ' ').trim();
const out = {};
[...document.querySelectorAll('div')].forEach(e => {
  const c = t(e.className);
  if (!(c.includes('px-5') && c.includes('py-3') && c.includes('border-b'))) return;
  if (e.children.length !== 2) return;
  const label = t(e.children[0].innerText);
  if (!label) return;
  out[label] = t(e.children[1].innerText);
});
return out;
"""


def _val(label):
    return (By.XPATH, "//div[normalize-space(text())='%s']/following-sibling::div[1]" % label)


def _at_account(driver):
    try:
        return ACCOUNT_URL_MARK in (driver.current_url or "")
    except Exception:
        return False


def _read_fields(driver):
    try:
        return driver.execute_script(READ_FIELDS_JS) or {}
    except Exception:
        return {}


def _goto_account(ctx, c=None):
    """大廳 -> MINE -> My info。"""
    W, cfg = ctx.W, ctx.config
    driver = ctx.driver
    if _at_account(driver):
        return True
    if not ctx.R.at_home(driver):
        ctx.go_home()
    ctx.P.close_all(driver)
    try:
        W.safe_click(driver, MINE_ICON, timeout=cfg.T_NORMAL)
        W.settle(1.2)
        W.safe_click(driver, MY_INFO_ROW, timeout=cfg.T_NORMAL)
        W.settle(1.2)
        W.wait_ready(driver, timeout=cfg.T_NORMAL)
    except W.SOFT_EXCEPTIONS:
        return False
    if c is not None and _at_account(driver):
        c.action("已進入 /account")
    return _at_account(driver)


def _close_modal(ctx, rounds=3):
    """關閉 modal：先試 modal 內的返回 icon，再試通用關閉鈕。"""
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    for _ in range(rounds):
        if not W.exists(driver, MODAL, 0):
            return True
        acted = False
        if W.exists(driver, MODAL_BACK, 0):
            try:
                W.safe_click(driver, MODAL_BACK, timeout=ctx.config.T_SHORT)
                acted = True
            except W.SOFT_EXCEPTIONS:
                pass
        if not acted:
            acted = bool(P.close_once(driver))
        if not acted:
            break
        W.settle(0.7)
    return not W.exists(driver, MODAL, 0)


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("G", "Account 個人資料")
    baseline = {}

    # ============================================================== G-0
    with ctx.case("G-0", "進入 /account 並記錄初始資料") as c:
        if not _goto_account(ctx, c):
            c.skip("無法進入 /account")
        c.check("已進入 %s" % driver.current_url)

        baseline = _read_fields(driver)
        if not baseline or all(v is None for v in baseline.values()):
            raise AssertionError("讀不到任何帳號欄位")
        for k, v in baseline.items():
            c.note("%-22s = %r" % (k, v))
        c.check("已記錄 %d 個欄位作為比對基準" % len([v for v in baseline.values() if v is not None]))

        data = dom_scan.scan_interactive(driver, "account", settle=0.5)
        path = dom_scan.save(data, cfg.PROBE_DIR, "account_interactive")
        c.check("可互動元素 %d 個（snapshot：%s）" % (data["count"], path))

    # ============================================================== G-1 ~ G-3
    for case_id, label, field, snap in REVERSIBLE:
        with ctx.case(case_id, "%s（L2 只開關 modal）" % label) as c:
            if not _goto_account(ctx):
                c.skip("無法進入 /account")
            _close_modal(ctx)

            info = W.probe(driver, _val(field), timeout=cfg.T_NORMAL)
            if not info["found"]:
                c.skip("/account 沒有 %s 這一列" % field)
            if not info["clickable"]:
                raise AssertionError("%s 不可點擊：%s" % (field, info))
            c.found("找到 %s（值=%r, clickable=%s）"
                    % (field, (info["text"] or "")[:30], info["clickable"]))

            before = _read_fields(driver)
            W.safe_click(driver, _val(field), timeout=cfg.T_NORMAL)
            c.action("已點擊 %s" % field)
            W.settle(1.2)
            W.note_toast(driver, c)

            if not W.exists(driver, MODAL, cfg.T_SHORT):
                raise AssertionError("點擊 %s 後沒有開啟 modal" % field)
            c.check("已開啟 modal")

            minfo = P.modal_info(driver)
            if minfo:
                c.note("modal imgs=%s buttons=%s"
                       % (minfo.get("imgs")[:5], minfo.get("buttons")[:5]))
            data = dom_scan.scan(driver, "account:%s" % snap, settle=0.6)
            p = dom_scan.save(data, cfg.PROBE_DIR, "account_%s" % snap)
            c.check("DOM snapshot：%s" % dom_scan.summarize(data))
            c.note("snapshot 檔案：%s" % p)
            for i in data.get("inputs", []):
                c.check("[L1 不輸入] input type=%r placeholder=%r"
                        % (i.get("type"), i.get("placeholder")))
            for b in data.get("buttons", []):
                if (b.get("text") or "").strip():
                    c.check("[L1 不點擊] modal 按鈕 %r" % b["text"].strip()[:24])

            if not _close_modal(ctx):
                raise AssertionError("%s 的 modal 關不掉" % field)
            c.check("modal 已關閉，未輸入也未儲存任何內容")

            after = _read_fields(driver)
            diff = [k for k in before if before.get(k) != after.get(k)]
            if diff:
                raise AssertionError("開關 modal 後欄位被改變：%s" % diff)
            c.check("帳號欄位未變動")

    # ============================================================== G-4
    with ctx.case("G-4", "Player ID（唯讀驗證）") as c:
        if not _goto_account(ctx):
            c.skip("無法進入 /account")
        info = W.probe(driver, _val("Player ID"), timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/account 沒有 Player ID")
        c.found("Player ID 存在")
        value = (info["text"] or "").strip()
        if not value:
            raise AssertionError("Player ID 沒有內容")
        c.check("值 = %r（純顯示，實測點擊無任何反應）" % value)
        c.check("displayed = %s / enabled = %s" % (info["displayed"], info["enabled"]))

    # ============================================================== G-5
    with ctx.case("G-5", "My invitation code（唯讀，不 Copy）") as c:
        if not _goto_account(ctx):
            c.skip("無法進入 /account")
        info = W.probe(driver, _val("My invitation code"), timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("/account 沒有 My invitation code")
        c.found("My invitation code 存在（含 img[alt='ic_copy_2'] 複製 icon）")
        value = (info["text"] or "").strip()
        if not value:
            raise AssertionError("邀請碼沒有內容")
        c.check("值 = %r" % value)
        c.check("displayed = %s / enabled = %s / clickable = %s"
                % (info["displayed"], info["enabled"], info["clickable"]))
        c.note("[SAFE-L1] 未點擊複製，也未分享至任何外部服務")

    # ============================================================== G-6 ~ G-8
    for case_id, label, field, reason in L1_ROWS:
        with ctx.case(case_id, "%s（L1 只驗證）" % label) as c:
            if not _goto_account(ctx):
                c.skip("無法進入 /account")
            info = W.probe(driver, _val(field), timeout=cfg.T_NORMAL)
            if not info["found"]:
                c.skip("/account 沒有 %s 這一列" % field)
            c.found("%s 存在（目前狀態 = %r）" % (field, (info["text"] or "").strip()[:20]))
            c.check("displayed = %s" % info["displayed"])
            c.check("enabled   = %s" % info["enabled"])
            c.check("clickable = %s" % info["clickable"])
            c.note("[SAFE-L1] 未點擊，原因：%s" % reason)

    # ============================================================== G-99
    with ctx.case("G-99", "Account 資料保護驗證") as c:
        if not _goto_account(ctx):
            c.skip("無法進入 /account")
        _close_modal(ctx)
        final = _read_fields(driver)
        for k, v in final.items():
            c.note("%-22s = %r" % (k, v))

        if not final:
            raise AssertionError("無法讀取 /account 欄位（可能未成功回到頁面），無法完成比對")
        diff = [(k, baseline.get(k), final.get(k))
                for k in baseline if baseline.get(k) != final.get(k)]
        if diff:
            raise AssertionError("測試前後帳號資料不一致：%s" % diff)
        c.check("測試前後 %d 個欄位完全一致，自動化未修改任何帳號資料"
                % len([v for v in baseline.values() if v is not None]))

        ctx.go_home()
        c.check("已回到大廳：%s" % driver.current_url)
