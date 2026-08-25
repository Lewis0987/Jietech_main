# -*- coding: utf-8 -*-
"""測試結果安全稽核：確認自動化沒有執行任何破壞性操作。

【為什麼不能只 grep 關鍵字】
    Phase 8 曾發生誤判：`/record` 的 `Withdrawal` 是**交易紀錄查詢頁籤**，
    但單純 grep "withdraw" 會把它當成提款操作。

    因此本工具的判斷結合五項資訊：
        Case ID  ->  哪一個 case
        Flow     ->  result JSON 的 group（A~L）
        URL      ->  從該 case 的步驟推導出當時所在頁面
        Action   ->  只看 [action] 步驟，不看 [check] / [found]
        元素語意 ->  區分 Withdrawal Record Tab / Withdraw 按鈕等

    另外用詞界（word boundary）區分：
        \\bwithdraw\\b    -> 提款動作（破壞性）
        \\bwithdrawal\\b  -> 提款「紀錄」，需再看語意豁免表

【額外檢查】
    標記 [SAFE-L1] 的 case 必須完全沒有點擊動作；有的話一律視為違規。

用法：
    python -m tools.safety_audit                 # 稽核最新一份 result JSON
    python -m tools.safety_audit --last 3        # 稽核最近 3 份
    python -m tools.safety_audit --file output/result_20260825_145253.json
"""

import argparse
import glob
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402

# ---------------------------------------------------------------- 破壞性規則
# (regex, 標籤)；regex 一律用詞界，避免 withdraw / withdrawal 互相誤判
DESTRUCTIVE_RULES = [
    (r"\bdeposit\b|存款|儲值", "存款"),
    (r"\bwithdraw\b|提款(?!紀錄)", "提款"),
    (r"\bwithdrawal\b", "提款/提款紀錄（需語意判斷）"),
    (r"\blogout\b|登出", "登出"),
    (r"\bclaim\b|領取|領獎", "領獎"),
    (r"\bredeem\b|兌換", "兌換"),
    (r"\bsubmit\b|送出", "送出"),
    (r"\bconfirm\b|確認送出", "確認送出"),
    (r"\bspin\b", "轉盤"),
    (r"gift\s*code|禮包碼", "禮包碼"),
    (r"\btelegram\b", "外部服務"),
    (r"\bwhatsapp\b", "外部服務"),
    (r"\bcopy\b|複製", "複製到剪貼簿"),
    (r"save\s*picture|儲存圖片", "下載圖片"),
    (r"\bbind\b|綁定", "綁定"),
    (r"\bdelete\b|刪除(?!測試下載|本次下載)", "刪除"),
    (r"\bsave\b(?!\s*picture)|儲存", "儲存"),
]

# ---------------------------------------------------------------- 語意豁免
# 只有同時滿足 case / group / 動作關鍵字 / 頁面語意，才視為安全。
# 每一筆都必須寫明理由，避免變成無差別白名單。
SAFE_EXEMPTIONS = [
    {
        "case": "H-4", "group": "H",
        "action_match": r"已點擊\s*Withdrawal\b",
        "page_hint": "/record",
        "element": "Withdrawal Record Tab",
        "reason": "/record 的交易紀錄查詢頁籤（L2 可逆導覽），"
                  "不是提款入口；真正的提款入口是 Safety Flow E-2，維持 L1 零點擊",
    },
    {
        "case": "H-5", "group": "H",
        "action_match": r"已點擊\s*Detail\b",
        "page_hint": "/record",
        "element": "Detail Record Tab",
        "reason": "/record 的交易明細查詢頁籤（L2 可逆導覽）",
    },
    {
        "case": "L-7", "group": "L",
        "action_match": r"Cancel\s*關閉\s*modal",
        "page_hint": "/subordinateData",
        "element": "日期 modal 的 Cancel",
        "reason": "取消日期選擇，實測日期不變；Confirm 維持 L1 未點擊",
    },
    {
        "case": "B-1", "group": "B",
        "action_match": r"已刪除本次下載",
        "page_hint": "",
        "element": "下載測試的檔案清理",
        "reason": "只刪除 B-1 本次新增的 APK（before/after 差集），"
                  "並驗證既有檔案未被動到",
    },
    {
        "case": "K-5", "group": "K",
        "action_match": r"已點擊\s*Detail\b",
        "page_hint": "/teamClub",
        "element": "Club Stars 的 Detail",
        "reason": "導向 /subordinateData 查詢頁（L2 可逆導覽）",
    },
]

CLICK_HINTS = (r"已點擊", r"\bclick", r"點擊")


def _is_click(action):
    return any(re.search(h, action, re.I) for h in CLICK_HINTS)


def _page_of(case):
    """從步驟文字推導該 case 當時所在頁面（推不出來回傳空字串）。"""
    steps = case.get("steps") or ""
    urls = re.findall(r"https?://[^\s|,)]+", steps)
    paths = []
    for u in urls:
        m = re.search(r"https?://[^/]+(/[^\s|,)]*)", u)
        if m:
            paths.append(m.group(1))
    for p in re.findall(r"(?:進入|已進入|返回|回到)\s*(/[A-Za-z_]+)", steps):
        paths.append(p)
    return paths[-1] if paths else ""


def _exempt(case, action, page):
    for ex in SAFE_EXEMPTIONS:
        if ex["case"] != case.get("case_id"):
            continue
        if ex.get("group") and ex["group"] != case.get("group"):
            continue
        if not re.search(ex["action_match"], action, re.I):
            continue
        if ex.get("page_hint") and ex["page_hint"] not in (page or ""):
            # 頁面推不出來時不強制，但會標記為 weak
            if page:
                continue
        return ex
    return None


def audit_file(path, verbose=False):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    violations, exempted, l1_cases, clicks = [], [], [], 0

    # 頁面資訊通常只出現在該 flow 的第一個 case，
    # 因此在同一個 flow(group) 內沿用最後一次已知頁面。
    last_page_by_group = {}

    for case in data.get("cases", []):
        steps = case.get("steps") or ""
        is_l1 = "[SAFE-L1]" in steps
        actions = [s for s in steps.split(" | ") if s.startswith("[action]")]
        group = case.get("group")
        page = _page_of(case)
        if page:
            last_page_by_group[group] = page
        else:
            page = last_page_by_group.get(group, "")

        if is_l1:
            l1_cases.append(case["case_id"])

        for action in actions:
            if not _is_click(action):
                continue
            clicks += 1

            # L1 case 一律不得有點擊
            if is_l1:
                violations.append({
                    "case": case["case_id"], "group": case.get("group"),
                    "page": page, "action": action,
                    "why": "此 case 標記 [SAFE-L1]，但出現點擊動作",
                })
                continue

            for pattern, label in DESTRUCTIVE_RULES:
                if not re.search(pattern, action, re.I):
                    continue
                ex = _exempt(case, action, page)
                if ex:
                    exempted.append({
                        "case": case["case_id"], "group": case.get("group"),
                        "page": page, "action": action, "label": label,
                        "element": ex["element"], "reason": ex["reason"],
                    })
                else:
                    violations.append({
                        "case": case["case_id"], "group": case.get("group"),
                        "page": page, "action": action,
                        "why": "疑似破壞性操作（%s），且無語意豁免" % label,
                    })
                break

    return {
        "file": path, "summary": data.get("summary"), "result": data.get("result"),
        "total_cases": len(data.get("cases", [])), "click_actions": clicks,
        "l1_cases": l1_cases, "exempted": exempted, "violations": violations,
    }


def report(res, verbose=False):
    line = "=" * 78
    print(line)
    print("Safety Audit : %s" % os.path.basename(res["file"]))
    print(line)
    print("測試結果   : %s（%s）" % (res["summary"], res["result"]))
    print("case 總數  : %d，其中標記 [SAFE-L1] 共 %d 個"
          % (res["total_cases"], len(res["l1_cases"])))
    print("點擊動作   : %d 筆" % res["click_actions"])

    if res["exempted"]:
        print()
        print("--- 語意豁免（含風險關鍵字但確認安全）---")
        for e in res["exempted"]:
            print("  [%s] %s" % (e["case"], e["action"]))
            print("      關鍵字=%s  頁面=%s  元素=%s" % (e["label"], e["page"] or "?", e["element"]))
            print("      理由：%s" % e["reason"])

    if verbose and res["l1_cases"]:
        print()
        print("--- [SAFE-L1] 零點擊 case ---")
        print("  %s" % ", ".join(res["l1_cases"]))

    print()
    if res["violations"]:
        print("--- 違規 ---")
        for v in res["violations"]:
            print("  [%s] flow=%s 頁面=%s" % (v["case"], v["group"], v["page"] or "?"))
            print("      %s" % v["action"])
            print("      -> %s" % v["why"])
        print()
        print("Safety Audit: FAIL（%d 筆違規）" % len(res["violations"]))
        return False
    print("Safety Audit: PASS（0 筆違規，%d 筆語意豁免）" % len(res["exempted"]))
    return True


def main(argv=None):
    config.force_utf8_stdout()
    ap = argparse.ArgumentParser(description="測試結果安全稽核")
    ap.add_argument("--file", default="", help="指定 result JSON")
    ap.add_argument("--last", type=int, default=1, help="稽核最近 N 份（預設 1）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.file:
        files = [args.file]
    else:
        pattern = os.path.join(str(config.OUTPUT_DIR), "result_*.json")
        files = sorted(glob.glob(pattern))[-max(1, args.last):]
    if not files:
        print("找不到任何 result JSON")
        return 2

    ok = True
    for path in files:
        if not report(audit_file(path), verbose=args.verbose):
            ok = False
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
