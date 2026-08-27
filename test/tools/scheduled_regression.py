# -*- coding: utf-8 -*-
"""Scheduled / CI Automatic Regression —— 自動化編排層。

【設計原則】
    本工具**不重複實作任何測試 Case**。
    真正的測試內容仍然由 full_site_test.py / flows/ / common/ 負責，
    安全稽核沿用 tools/safety_audit.py，不建立第二套。

    scheduled_regression 只做編排：
        1. 以 Headless 呼叫既有 full_site_test.py（全新行程 = 全新 Driver）
        2. 取得該輪產生的 result JSON
        3. 執行既有 Safety Audit
        4. 與 Baseline 做「逐 Case」比較
        5. 檢查 Downloads 是否有測試殘留
        6. 產生 Automation Summary（JSON + CSV）
        7. 回傳明確 Exit Code

【Raw Result 與 Automation Status 是兩個概念】
    Raw Result             : 135 / 104 PASS / 2 FAIL / 29 SKIP  <- 原始事實，絕不篡改
    Baseline Comparison    : C-00 / I-00 屬 KNOWN FAIL          <- 是否出現「新的」問題
    Final Automation Status: PASS（No New Regression）

    因此 CI 判定**不能**用 `raw FAIL > 0 -> pipeline FAIL` 這種邏輯。

【Baseline 絕不自動更新】
    本工具只會「讀取」baseline。
    要更新必須人工明確執行 --init-baseline，
    否則真正的 Regression 會被自動接受而消失。

用法：
    python -m tools.scheduled_regression                    # 正式自動 Regression
    python -m tools.scheduled_regression --init-baseline    # 人工建立/更新 Baseline
    python -m tools.scheduled_regression --from-result <result.json>   # 只比對，不跑測試
    python -m tools.scheduled_regression --baseline <baseline.json>
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402
from common import download_utils as DL          # noqa: E402
from tools import safety_audit                   # noqa: E402

DEFAULT_FLOWS = ("popup,header,banner,menu,safety,mine,"
                 "account,record,promo,task,earn,subordinate")

BASELINE_DIR = os.path.join(BASE_DIR, "baseline")
BASELINE_FILE = os.path.join(BASELINE_DIR, "regression_baseline.json")
AUTOMATION_DIR = os.path.join(str(config.OUTPUT_DIR), "automation")

# ---------------------------------------------------------------- 比較分類
EXPECTED_PASS = "EXPECTED PASS"
EXPECTED_FAIL = "EXPECTED FAIL"      # KNOWN STABLE FAIL
EXPECTED_SKIP = "EXPECTED SKIP"
NEW_FAIL = "NEW FAIL"
NEW_SKIP = "NEW SKIP"
RECOVERED = "RECOVERED"
STATUS_CHANGED = "STATUS CHANGED"
MISSING_CASE = "MISSING CASE"
NEW_CASE = "NEW CASE"

# 會讓 Automation 判定失敗的分類
BLOCKING = (NEW_FAIL, MISSING_CASE)
# 需要人工注意但不擋 CI 的分類
WARNING = (NEW_SKIP, RECOVERED, STATUS_CHANGED, NEW_CASE)

# Exit code 契約
EXIT_OK = 0        # 沒有新 Regression、Safety PASS、Runner 正常
EXIT_REGRESSION = 1  # NEW FAIL / MISSING CASE / Safety violation
EXIT_ERROR = 2     # Runner / Browser / Result 解析失敗


# ================================================================ Baseline
def load_baseline(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_baseline(result_json, source_path):
    cases = {}
    for c in result_json.get("cases", []):
        cases[c["case_id"]] = c["status"]
    known_fail = sorted(cid for cid, st in cases.items() if st == "FAIL")
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_result": os.path.basename(source_path),
        "note": ("Baseline 只能由人工執行 --init-baseline 更新；"
                 "自動 Regression 永遠不會改寫這個檔案。"),
        "totals": result_json.get("summary"),
        "known_fail": known_fail,
        "cases": cases,
    }


def save_baseline(baseline, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    return path


# ================================================================ 比較
def compare(baseline, result_json):
    """逐 Case 比較。只比總數會漏掉『一個 PASS 變 FAIL、另一個 FAIL 變 PASS』。"""
    expected = dict(baseline.get("cases") or {})
    actual = {}
    detail = {}
    for c in result_json.get("cases", []):
        actual[c["case_id"]] = c["status"]
        detail[c["case_id"]] = c

    rows = []
    for cid in sorted(set(list(expected) + list(actual))):
        exp = expected.get(cid)
        act = actual.get(cid)

        if exp is None:
            klass = NEW_CASE
        elif act is None:
            klass = MISSING_CASE
        elif exp == act:
            klass = {"PASS": EXPECTED_PASS, "FAIL": EXPECTED_FAIL,
                     "SKIP": EXPECTED_SKIP}.get(act, STATUS_CHANGED)
        elif act == "FAIL":
            klass = NEW_FAIL
        elif exp == "FAIL" and act == "PASS":
            klass = RECOVERED
        elif exp == "PASS" and act == "SKIP":
            klass = NEW_SKIP
        else:
            klass = STATUS_CHANGED

        c = detail.get(cid, {})
        rows.append({
            "case_id": cid,
            "group": c.get("group", ""),
            "name": c.get("name", ""),
            "expected": exp or "-",
            "actual": act or "-",
            "classification": klass,
            "error_type": c.get("error_type", ""),
            "error_msg": c.get("error_msg", ""),
            "elapsed_s": c.get("duration_s", ""),
            "screenshot": c.get("screenshot", ""),
        })
    return rows


def tally(rows):
    out = {}
    for r in rows:
        out[r["classification"]] = out.get(r["classification"], 0) + 1
    return out


# ================================================================ 執行
def run_regression(flows, headless=True):
    """呼叫既有 full_site_test.py。回傳 (info, error)。"""
    cmd = [sys.executable, "full_site_test.py", "--flows", flows]
    if headless:
        cmd.append("--headless")

    print("執行：%s" % " ".join(cmd[1:]))
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    except Exception as e:
        return None, "無法啟動 full_site_test.py：%s" % e
    wall = round(time.time() - started, 2)

    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"^JSON\s*:\s*(.+\.json)\s*$", out, re.M)
    if not m:
        return None, ("full_site_test.py 沒有輸出 result JSON 路徑（exit=%s）；"
                      "最後 300 字：%s" % (proc.returncode, out[-300:]))
    return {"json_path": m.group(1).strip(), "exit_code": proc.returncode,
            "wall_seconds": wall, "stdout_tail": out[-2000:]}, None


def download_residual(before):
    """檢查本次是否留下測試下載殘留。"""
    after = DL.snapshot(config.DOWNLOAD_PATH)
    new = sorted(after - set(before or ()))
    suspicious = [f for f in new
                  if f.lower().endswith(config.DOWNLOAD_EXTENSIONS)
                  or DL.is_partial(f)]
    return {"new_files": new, "residual": suspicious, "count": len(suspicious)}


# ================================================================ 報告
def write_reports(payload, out_dir, run_id):
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "automation_%s.json" % run_id)
    csv_path = os.path.join(out_dir, "automation_%s.csv" % run_id)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    fields = ["case_id", "group", "name", "expected", "actual",
              "classification", "elapsed_s", "error_type", "error_msg",
              "screenshot"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in payload.get("cases", []):
            w.writerow(dict((k, r.get(k, "")) for k in fields))
    return json_path, csv_path


def report(payload):
    line = "=" * 78
    print()
    print(line)
    print("Automation Regression Summary")
    print(line)
    m = payload["meta"]
    print("開始 / 結束 : %s -> %s（%.2fs）"
          % (m["start_time"], m["end_time"], m["duration_s"]))
    print("模式        : %s" % m["mode"])
    print("Baseline    : %s（建立於 %s）" % (m["baseline_file"], m.get("baseline_created_at")))

    raw = payload["raw_result"]
    print()
    print("--- Raw Result（原始事實，未經任何修改）---")
    print("Total %s / PASS %s / FAIL %s / SKIP %s"
          % (raw.get("TOTAL"), raw.get("PASS"), raw.get("FAIL"), raw.get("SKIP")))
    print("result JSON : %s" % m.get("result_json"))

    print()
    print("--- Baseline Comparison（逐 Case）---")
    for k, v in sorted(payload["comparison"].items()):
        print("  %-16s %d" % (k, v))

    for klass, title in ((NEW_FAIL, "NEW FAIL（新的 Regression）"),
                         (MISSING_CASE, "MISSING CASE（Baseline 有但本次沒跑到）"),
                         (NEW_SKIP, "NEW SKIP（覆蓋率下降，需人工確認）"),
                         (RECOVERED, "RECOVERED（Known Fail 已恢復，需人工確認 Baseline）"),
                         (STATUS_CHANGED, "STATUS CHANGED"),
                         (NEW_CASE, "NEW CASE（新增 Case，需人工更新 Baseline）")):
        hits = [r for r in payload["cases"] if r["classification"] == klass]
        if not hits:
            continue
        print()
        print("--- %s ---" % title)
        for r in hits:
            print("  [%s] %s  expected=%s actual=%s"
                  % (r["case_id"], r["name"][:36], r["expected"], r["actual"]))
            if r.get("error_msg"):
                print("      %s: %s" % (r.get("error_type"), r["error_msg"][:110]))
            if r.get("screenshot"):
                print("      screenshot: %s" % r["screenshot"])

    known = [r["case_id"] for r in payload["cases"]
             if r["classification"] == EXPECTED_FAIL]
    if known:
        print()
        print("--- KNOWN STABLE FAIL（符合 Baseline，不算新 Regression）---")
        print("  %s" % ", ".join(known))
        print("  註：Raw Result 仍然保持 FAIL，未被改寫成 PASS。")

    s = payload["safety"]
    print()
    print("--- Safety Audit ---")
    print("  結果：%s（違規 %d，語意豁免 %d）"
          % (s["result"], s["violations"], s["exempted"]))
    for v in s.get("violation_detail", [])[:5]:
        print("    [%s] %s -> %s" % (v.get("case"), v.get("action", "")[:60], v.get("why")))

    d = payload["download"]
    print()
    print("--- Download 殘留 ---")
    print("  本次新增檔案 %d 個，其中疑似測試殘留 %d 個 %s"
          % (len(d["new_files"]), d["count"], d["residual"] or ""))

    print()
    print(line)
    print("Final Automation Status : %s" % payload["final_status"])
    print("Exit Code               : %s" % payload["exit_code"])
    print(line)


# ================================================================ main
def main(argv=None):
    config.force_utf8_stdout()
    ap = argparse.ArgumentParser(description="Scheduled / CI Automatic Regression")
    ap.add_argument("--flows", default=DEFAULT_FLOWS)
    ap.add_argument("--baseline", default=BASELINE_FILE)
    ap.add_argument("--headed", action="store_true",
                    help="改用有頭模式（預設 Headless）")
    ap.add_argument("--from-result", default="",
                    help="不跑測試，直接用既有 result JSON 做比對（驗證用）")
    ap.add_argument("--init-baseline", action="store_true",
                    help="【人工操作】用本次結果建立 / 更新 Baseline")
    ap.add_argument("--out-dir", default=AUTOMATION_DIR)
    args = ap.parse_args(argv)

    start = datetime.now()
    run_id = start.strftime("%Y%m%d_%H%M%S")
    mode = "headed" if args.headed else "headless"

    print("=" * 78)
    print("Scheduled Regression")
    print("=" * 78)
    print("模式     : %s" % mode)
    print("Baseline : %s" % args.baseline)

    # ---------------- 取得 result ----------------
    dl_before = DL.snapshot(config.DOWNLOAD_PATH)
    run_info = {"json_path": args.from_result, "exit_code": None,
                "wall_seconds": 0.0}
    if args.from_result:
        print("來源     : 既有 result（不重新執行測試）%s" % args.from_result)
        if not os.path.exists(args.from_result):
            print("找不到指定的 result JSON")
            return EXIT_ERROR
    else:
        run_info, err = run_regression(args.flows, headless=not args.headed)
        if err:
            print("\nRunner 失敗：%s" % err)
            return EXIT_ERROR

    try:
        with open(run_info["json_path"], encoding="utf-8") as f:
            result_json = json.load(f)
    except Exception as e:
        print("\n無法解析 result JSON：%s" % e)
        return EXIT_ERROR

    # ---------------- 人工建立 Baseline ----------------
    if args.init_baseline:
        baseline = build_baseline(result_json, run_info["json_path"])
        path = save_baseline(baseline, args.baseline)
        print()
        print("已建立 / 更新 Baseline：%s" % path)
        print("  totals    : %s" % baseline["totals"])
        print("  known_fail: %s" % baseline["known_fail"])
        print("  cases     : %d 個" % len(baseline["cases"]))
        print("\n注意：Baseline 只能像這樣由人工明確更新，自動 Regression 不會改寫它。")
        return EXIT_OK

    baseline = load_baseline(args.baseline)
    if baseline is None:
        print("\n找不到 Baseline：%s" % args.baseline)
        print("請先人工執行：python -m tools.scheduled_regression --init-baseline")
        return EXIT_ERROR

    # ---------------- 比較 / 稽核 / 殘留 ----------------
    rows = compare(baseline, result_json)
    counts = tally(rows)

    try:
        audit = safety_audit.audit_file(run_info["json_path"])
        safety = {"result": "PASS" if not audit["violations"] else "FAIL",
                  "violations": len(audit["violations"]),
                  "exempted": len(audit["exempted"]),
                  "violation_detail": audit["violations"]}
    except Exception as e:
        safety = {"result": "ERROR", "violations": -1, "exempted": 0,
                  "violation_detail": [{"why": str(e)}]}

    residual = download_residual(dl_before)

    blocking = sum(counts.get(k, 0) for k in BLOCKING)
    warnings = sum(counts.get(k, 0) for k in WARNING)
    safety_bad = safety["result"] != "PASS"

    if blocking or safety_bad:
        final = "FAIL"
        exit_code = EXIT_REGRESSION
    elif warnings:
        final = "PASS（有需人工確認的變化）"
        exit_code = EXIT_OK
    else:
        final = "PASS（No New Regression）"
        exit_code = EXIT_OK

    end = datetime.now()
    payload = {
        "meta": {
            "run_id": run_id, "mode": mode,
            "start_time": start.isoformat(timespec="seconds"),
            "end_time": end.isoformat(timespec="seconds"),
            "duration_s": round((end - start).total_seconds(), 2),
            "regression_wall_s": run_info.get("wall_seconds"),
            "full_site_test_exit": run_info.get("exit_code"),
            "result_json": run_info["json_path"],
            "baseline_file": args.baseline,
            "baseline_created_at": baseline.get("created_at"),
            "flows": args.flows,
        },
        "raw_result": result_json.get("summary") or {},
        "comparison": counts,
        "known_fail_baseline": baseline.get("known_fail", []),
        "new_fail": [r["case_id"] for r in rows if r["classification"] == NEW_FAIL],
        "recovered": [r["case_id"] for r in rows if r["classification"] == RECOVERED],
        "missing_case": [r["case_id"] for r in rows if r["classification"] == MISSING_CASE],
        "new_case": [r["case_id"] for r in rows if r["classification"] == NEW_CASE],
        "new_skip": [r["case_id"] for r in rows if r["classification"] == NEW_SKIP],
        "safety": safety,
        "download": residual,
        "final_status": final,
        "exit_code": exit_code,
        "cases": rows,
    }

    json_path, csv_path = write_reports(payload, args.out_dir, run_id)
    report(payload)
    print("Automation JSON : %s" % json_path)
    print("Automation CSV  : %s" % csv_path)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
