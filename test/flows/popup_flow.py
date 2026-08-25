# -*- coding: utf-8 -*-
"""[A] 首頁 Popup 流程。

由 IN【V6】.py 的 A 區搬入，locator 完全沿用（見 common/popup_utils.KNOWN_POPUPS）。

與原始版本的差異：
  * 原本 8 段複製貼上的「首充內彈關閉」改由 popup_utils 統一處理。
  * popup 沒出現時記為 SKIP，不再只是印一行「未偵測活動元素」。
  * 每個 case 都有 Post-condition：關閉後必須驗證該 popup 已消失。

本站 popup 會排隊連續彈出，所以：
  A-0 先重新載入大廳，讓 popup 有機會出現
  A-1..A-7 逐一處理已知 popup
  A-8 收尾，確保畫面穩定無殘留 popup
"""

# 執行順序 = IN【V6】.py 的原始順序
POPUP_CASES = [
    ("A-1", "subscribe",         "Subscribe / Later"),
    ("A-2", "prize_wheel",       "Prize wheel 充值大輪盤"),
    ("A-3", "first_recharge_vb", "First recharge 首充"),
    ("A-4", "mission",           "Mission 任務中心"),
    ("A-5", "club",              "Club 俱樂部"),
    ("A-6", "telegram",          "Telegram 訂閱"),
    ("A-7", "jackpot",           "Jackpot"),
]

# popup 之間的等待：關掉一個之後，下一個需要一點時間才會彈出
QUEUE_WAIT = 1.5
# 佇列最多處理幾輪（防止 popup 無限重生時空轉）
MAX_ROUNDS = 12


def run(ctx):
    W, P, D = ctx.W, ctx.P, ctx.D
    driver = ctx.driver

    ctx.group("A", "首頁 Popup")

    # ---------------------------------------------------------- A-0
    with ctx.case("A-0", "重新載入大廳以觸發 popup") as c:
        c.action("driver.get(%s)" % ctx.home_url)
        url = D.open_url(driver, ctx.home_url, timeout=ctx.config.T_PAGE_LOAD)
        c.check("current_url = %s" % url)
        # 給前端渲染 + popup 排程一點時間（UI animation，屬允許的短暫等待）
        W.settle(2.0)
        detected = P.detect(driver, timeout=ctx.config.T_SHORT)
        c.check("初始偵測到 popup：%s" % (detected or "無"))

    # ---------------------------------------------------------- A-1..A-7
    # 本站 popup 是「關一個 -> 下一個才彈出」的佇列，
    # 因此不能用固定順序逐一等待（會在該 popup 還沒輪到時就誤判 NOT PRESENT）。
    # 作法：每關掉一個就重新偵測，實際出現的先處理；跑完之後再補上未出現者的 SKIP。
    handled = set()
    rounds = 0

    while len(handled) < len(POPUP_CASES) and rounds < MAX_ROUNDS:
        rounds += 1
        detected = P.detect(driver, timeout=ctx.config.T_SHORT if rounds == 1 else 1.5)
        detected = [k for k in detected if k not in handled]
        if not detected:
            break

        target = None
        for case_id, key, label in POPUP_CASES:
            if key in detected:
                target = (case_id, key, label)
                break
        if target is None:
            break                      # 偵測到的不在 POPUP_CASES 內，交給 A-8 收尾

        case_id, key, label = target
        handled.add(key)

        with ctx.case(case_id, label) as c:
            popup = P.POPUP_BY_KEY[key]
            c.found("偵測到 %s：%s" % (label, popup["locator"][1]))

            # Action
            closed = P.close_specific(driver, key, timeout=1)
            if not closed:
                # 關閉鈕點了但 popup 還在，或根本找不到關閉鈕
                if P.popup_visible(driver, popup, 0):
                    raise AssertionError("找到 %s 但無法關閉（關閉鈕不存在或點擊無效）" % label)
                c.action("popup 已自行消失")
            else:
                c.action("已點擊關閉鈕")

            # Post-condition
            W.settle(0.4)
            if P.popup_visible(driver, popup, 0):
                raise AssertionError("已點擊關閉，但 %s 仍然存在" % label)
            c.check("%s 已消失" % label)

        # 讓排隊中的下一個 popup 有時間彈出（在 case 之外，不計入該 case 耗時）
        W.settle(QUEUE_WAIT)

    # 未出現的 popup 統一補上 SKIP，維持 A-1..A-7 案例完整
    for case_id, key, label in POPUP_CASES:
        if key in handled:
            continue
        with ctx.case(case_id, label) as c:
            c.skip("本次未出現（NOT PRESENT，佇列共偵測 %s 輪）" % rounds)

    # ---------------------------------------------------------- A-8
    with ctx.case("A-8", "清除殘留 popup 至畫面穩定") as c:
        remaining = P.detect(driver, timeout=0)
        c.found("剩餘已知 popup：%s" % (remaining or "無"))
        closed = P.close_all(driver, log=ctx.log)
        c.action("追加關閉 %s 個" % closed)
        W.settle(0.5)

        still = P.detect(driver, timeout=0)
        if still:
            raise AssertionError("仍有 popup 未關閉：%s" % still)
        c.check("已知 popup 皆已關閉")

        if P.has_close_button(driver):
            c.note("畫面仍有未知的關閉鈕（非 KNOWN_POPUPS，待 Phase 3 probe 確認）")
        else:
            c.check("畫面無殘留關閉鈕")

        # Recovery：確保停在穩定頁面
        if not ctx.R.at_home(driver):
            ctx.go_home()
        c.check("停留於大廳：%s" % driver.current_url)
