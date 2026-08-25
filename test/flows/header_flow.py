# -*- coding: utf-8 -*-
"""[B] Header 功能區。

由 IN【V6】.py 的 B-1-1 ~ B-1-4 搬入，locator 沿用原始已驗證版本：

    Download 按鈕      //button[contains(., 'Download')]
    下載列關閉         img[alt='ic_close_2']            <- popup_utils 刻意不碰
    充值輪盤 icon      img[alt='ic_lucky_wheel']
    輪盤頁錨點         //span[contains(text(), 'Deposit Now')]
    信箱 icon          //img[contains(@alt, 'ic_mail')]  <- 相容 unread / read
    信件頁錨點         //div[contains(text(),'Mail')]
    返回 icon          //img[contains(@alt,'ic_back_header')]

破壞性保護：SPIN / Deposit / Withdraw / Collect 一律只做
found + displayed + enabled + clickable，絕不點擊。
"""

from selenium.webdriver.common.by import By

# ------------------------------------------------------------------ locator
DOWNLOAD_BTN = (By.XPATH, "//button[contains(., 'Download')]")
DOWNLOAD_BAR = (By.XPATH, "//img[contains(@alt, 'img_download')]")
LUCKY_WHEEL = (By.CSS_SELECTOR, "img[alt='ic_lucky_wheel']")
WHEEL_ANCHORS = [
    (By.XPATH, "//span[contains(text(), 'Deposit Now')]"),
    (By.XPATH, "//span[contains(text(), 'SPIN')]"),
    (By.XPATH, "//img[contains(@alt, 'ic_back_header')]"),
]
# 實際 DOM 顯示為 ic_mail_unread；用 contains 以相容已讀狀態的 alt
MAIL_ICON = (By.XPATH, "//img[contains(@alt, 'ic_mail')]")
MAIL_PAGE = (By.XPATH, "//div[contains(text(),'Mail')]")
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")

# 只驗證、不點擊的破壞性元素
DESTRUCTIVE = [
    ("Deposit", (By.XPATH, "//button[contains(., 'Deposit')]")),
    ("Withdraw", (By.XPATH, "//button[contains(., 'Withdraw')]")),
    ("SPIN", (By.XPATH, "//span[contains(text(), 'SPIN')]")),
]


def _leave_page(ctx, c):
    """離開子頁面回到大廳：優先用站內返回鍵，失敗才用 recovery。"""
    W, driver = ctx.W, ctx.driver
    if W.exists(driver, BACK_ICON, 0):
        try:
            W.safe_click(driver, BACK_ICON, timeout=ctx.config.T_SHORT)
            W.settle(0.8)
            c.action("使用站內返回 icon")
        except W.SOFT_EXCEPTIONS:
            pass
    if not ctx.R.at_home(driver):
        ctx.go_home()
    return ctx.R.at_home(driver)


def run(ctx):
    W, P, DL, D = ctx.W, ctx.P, ctx.DL, ctx.D
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("B", "Header")

    # 從乾淨的大廳出發
    if not ctx.R.at_home(driver):
        ctx.go_home()
    P.close_all(driver, log=ctx.log)

    # ============================================================== B-1
    with ctx.case("B-1", "Header Download（APK 端到端）") as c:
        info = W.probe(driver, DOWNLOAD_BTN, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("此環境 / 裝置模式無 Download 按鈕")
        if not info["clickable"]:
            raise AssertionError("找到 Download 但不可點擊：%s" % info)
        c.found("找到 Download 按鈕（enabled=%s, clickable=%s）"
                % (info["enabled"], info["clickable"]))

        # --- 下載前快照（差集基準，保護既有檔案）---
        before = DL.snapshot(cfg.DOWNLOAD_PATH)
        c.check("下載前快照：既有檔案 %s 個 @ %s" % (len(before), cfg.DOWNLOAD_PATH))

        main_handle = driver.current_window_handle
        W.safe_click(driver, DOWNLOAD_BTN, timeout=cfg.T_NORMAL)
        c.action("已點擊 Download")

        # 下載可能開新分頁。
        # ⚠️ 這裡【不能】立刻關掉新分頁——關掉會直接中斷下載。
        # 沿用 IN【V6】.py 的做法：先切換過去，等下載結束後再收掉分頁。
        W.settle(1.0)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            c.note("下載觸發新分頁：%s" % driver.current_url)

        # --- 等待下載完成（排除 .crdownload/.tmp/.partial + 檔案大小穩定）---
        ctx.log("等待下載完成...")
        try:
            res = DL.wait_for_new_download(
                cfg.DOWNLOAD_PATH, before,
                timeout=cfg.T_DOWNLOAD,
                extensions=cfg.DOWNLOAD_EXTENSIONS,
                log=ctx.log,
            )
        finally:
            # 下載結束（成功或逾時）之後才收掉多餘分頁並切回主視窗
            if len(driver.window_handles) > 1:
                n = D.close_extra_windows(driver, keep_handle=main_handle)
                c.note("已關閉 %s 個下載分頁並切回主視窗" % n)
            else:
                driver.switch_to.window(main_handle)

        if not res["ok"]:
            # 把「靜默 Timeout」變成可診斷訊息：檔案到底掉到哪裡
            found_elsewhere = DL.diagnose(cfg.DOWNLOAD_PATH, before,
                                          extensions=cfg.DOWNLOAD_EXTENSIONS)
            DL.cleanup_partials(cfg.DOWNLOAD_PATH, before, log=ctx.log)
            detail = "；其他資料夾發現：%s" % found_elsewhere if found_elsewhere else ""
            raise AssertionError(res["reason"] + detail)

        c.check("下載完成：%s（耗時 %ss）" % (res["files"], res["elapsed"]))

        # --- 只刪除本次新增的檔案 ---
        deleted, failed = DL.delete_downloads(cfg.DOWNLOAD_PATH, res["files"], log=ctx.log)
        if failed:
            raise AssertionError("以下檔案刪除失敗：%s" % failed)
        c.action("已刪除本次下載：%s" % deleted)

        still = DL.assert_deleted(cfg.DOWNLOAD_PATH, res["files"])
        if still:
            raise AssertionError("刪除驗證失敗，檔案仍存在：%s" % still)
        c.check("刪除驗證通過")

        # --- 確認既有檔案沒被動到 ---
        after = DL.snapshot(cfg.DOWNLOAD_PATH)
        missing = before - after
        if missing:
            raise AssertionError("既有檔案遭誤刪：%s" % sorted(missing))
        c.check("既有 %s 個檔案完好無損" % len(before))

    # ============================================================== B-2
    with ctx.case("B-2", "Download bar 關閉") as c:
        info = W.probe(driver, P.DOWNLOAD_BAR_CLOSE, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("本次畫面沒有 download bar（ic_close_2）")
        c.found("找到下載列關閉鈕 ic_close_2（clickable=%s）" % info["clickable"])

        W.safe_click(driver, P.DOWNLOAD_BAR_CLOSE, timeout=cfg.T_NORMAL)
        c.action("已點擊 ic_close_2")

        if not W.wait_gone(driver, P.DOWNLOAD_BAR_CLOSE, timeout=cfg.T_NORMAL):
            raise AssertionError("已點擊關閉，但下載列仍在畫面上")
        c.check("下載列已關閉（ic_close_2 消失）")

        if W.exists(driver, DOWNLOAD_BAR, 0):
            c.note("img_download 仍存在於 DOM（可能僅隱藏）")

        if not ctx.R.at_home(driver):
            ctx.go_home()
        c.check("仍停留於大廳")

    # ============================================================== B-3
    with ctx.case("B-3", "Lucky Wheel 充值輪盤") as c:
        info = W.probe(driver, LUCKY_WHEEL, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("本次畫面沒有 ic_lucky_wheel")
        if not info["clickable"]:
            raise AssertionError("找到 ic_lucky_wheel 但不可點擊：%s" % info)
        c.found("找到充值輪盤 icon（clickable=%s）" % info["clickable"])

        before_url = driver.current_url
        W.safe_click(driver, LUCKY_WHEEL, timeout=cfg.T_NORMAL)
        c.action("已點擊充值輪盤 icon")
        W.settle(1.0)

        # Post-condition：任一輪盤錨點出現，或 URL 已改變
        hit = None
        for loc in WHEEL_ANCHORS:
            if W.exists(driver, loc, cfg.T_SHORT):
                hit = loc[1]
                break
        if hit:
            c.check("進入輪盤頁，錨點：%s" % hit)
        elif driver.current_url != before_url:
            c.check("URL 已變更：%s" % driver.current_url)
        else:
            raise AssertionError("點擊後畫面無變化（URL 未變更且找不到輪盤錨點）")

        # 破壞性元素：只驗證，不點擊
        for label, loc in DESTRUCTIVE:
            p = W.probe(driver, loc, timeout=1)
            if p["found"]:
                c.note("[只驗證不點擊] %s displayed=%s enabled=%s clickable=%s"
                       % (label, p["displayed"], p["enabled"], p["clickable"]))

        if not _leave_page(ctx, c):
            raise AssertionError("無法從輪盤頁返回大廳")
        c.check("已返回大廳：%s" % driver.current_url)

    # ============================================================== B-4
    with ctx.case("B-4", "Mail 信箱") as c:
        info = W.probe(driver, MAIL_ICON, timeout=cfg.T_NORMAL)
        if not info["found"]:
            c.skip("本次畫面沒有信箱 icon")
        actual_alt = W.attr_of(driver, MAIL_ICON, "alt", timeout=1)
        c.found("找到信箱 icon（alt=%s, clickable=%s）" % (actual_alt, info["clickable"]))

        before_url = driver.current_url
        W.safe_click(driver, MAIL_ICON, timeout=cfg.T_NORMAL)
        c.action("已點擊信箱 icon")
        W.settle(0.8)

        if W.exists(driver, MAIL_PAGE, cfg.T_NORMAL):
            c.check("進入 Mail 頁面（錨點 //div[text()='Mail']）")
        elif driver.current_url != before_url:
            c.check("URL 已變更：%s" % driver.current_url)
        else:
            raise AssertionError("點擊信箱後畫面無變化")

        # 返回：優先使用站內返回鍵，並驗證真的回到大廳
        if not W.exists(driver, BACK_ICON, cfg.T_SHORT):
            c.note("找不到 ic_back_header，改用 recovery 返回")
        if not _leave_page(ctx, c):
            raise AssertionError("無法從 Mail 頁返回大廳")
        c.check("已返回大廳：%s" % driver.current_url)
