# -*- coding: utf-8 -*-
"""Stability / Flaky Test Validation —— 連續執行既有 Full Regression 並比對結果。

【設計原則】
    本工具**不重複實作任何測試 Case**。
    真正的測試內容仍然由 full_site_test.py / flows/ / common/ 負責。

    stability_runner 只做四件事：
        Run      -> 以子行程呼叫既有 full_site_test.py（每輪都是全新 Python
                    行程，因此保證每輪都是全新的 Chrome Driver 與 session）
        Collect  -> 從該輪 stdout 取得它產生的 result JSON
        Compare  -> 逐 Case 比對各輪狀態與耗時
        Report   -> 輸出 stability_<ts>.csv / .json 到 output/stability/

    原始的 result_*.csv / result_*.json 完全保留，不會被覆蓋。

【Case 穩定性分類】
    STABLE PASS  每輪都 PASS
    STABLE FAIL  每輪都 FAIL，且 error_type 一致（可穩定重現的缺陷）
    STABLE SKIP  每輪都 SKIP，且原因一致
    FLAKY        跨輪狀態不一致，或同樣 FAIL 但失敗原因不同

【Safety Audit】
    每輪結束後直接呼叫既有 tools.safety_audit.audit_file()，
    不另外實作第二套稽核。

用法：
    python -m tools.stability_runner --runs 3 --modes headed
    python -m tools.stability_runner --runs 3 --modes headed,headless
    python -m tools.stability_runner --runs 2 --modes headed --flows record
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
from tools import safety_audit                   # noqa: E402

DEFAULT_FLOWS = ("popup,header,banner,menu,safety,mine,"
                 "account,record,promo,task,earn,subordinate")

STABLE_PASS = "STABLE PASS"
STABLE_FAIL = "STABLE FAIL"
STABLE_SKIP = "STABLE SKIP"
FLAKY = "FLAKY"
PARTIAL = "PARTIAL"          # 該 case 沒有在每一輪都出現


def _run_once(mode, flows, run_no, total_runs):
    """呼叫一次既有的 full_site_test.py（全新行程 = 全新 driver）。"""
    cmd = [sys.executable, "full_site_test.py", "--flows", flows]
    if mode == "headless":
        cmd.append("--headless")

    print("\n" + "-" * 70)
    print("[%s] Run %d/%d 開始：%s" % (mode, run_no, total_runs, " ".join(cmd[1:])))
    print("-" * 70)

    started = time.time()
    proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    wall = round(time.time() - started, 2)

    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"^JSON\s*:\s*(.+\.json)\s*$", out, re.M)
    json_path = m.group(1).strip() if m else None

    summary = None
    ms = re.search(r"^Total\s*:\s*(\d+)", out, re.M)
    if ms:
        def grab(label):
            g = re.search(r"^%s\s*:\s*(\d+)" % label, out, re.M)
            return int(g.group(1)) if g else None
        summary = {"TOTAL": int(ms.group(1)), "PASS": grab("PASS"),
                   "FAIL": grab("FAIL"), "SKIP": grab("SKIP")}

    print("[%s] Run %d/%d 結束：exit=%s wall=%ss summary=%s"
          % (mode, run_no, total_runs, proc.returncode, wall, summary))
    if not json_path:
        print("  ⚠ 這一輪沒有取得 result JSON 路徑，最後 400 字輸出：")
        print("  " + out[-400:].replace("\n", "\n  "))

    return {"mode": mode, "run": run_no, "exit_code": proc.returncode,
            "wall_seconds": wall, "json_path": json_path,
            "printed_summary": summary}


def _load_cases(json_path):
    """讀回該輪的 result JSON（沿用既有格式，不另存一份）。"""
    if not json_path or not os.path.exists(json_path):
        return None, {}
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    cases = {}
    for c in data.get("cases", []):
        cases[c["case_id"]] = c
    return data, cases


def _classify(case_id, per_run):
    """per_run: [{run, mode, status, error_type, error_msg, duration}]，可能有缺輪。"""
    statuses = [r["status"] for r in per_run]
    unique = set(statuses)

    if len(per_run) == 0:
        return PARTIAL, "沒有任何一輪執行到"
    if len(unique) > 1:
        return FLAKY, "跨輪狀態不一致：%s" % ", ".join(
            "%s#%d=%s" % (r["mode"], r["run"], r["status"]) for r in per_run)

    status = statuses[0]
    if status == "PASS":
        return STABLE_PASS, ""
    if status == "FAIL":
        types = set(r["error_type"] for r in per_run)
        if len(types) > 1:
            return FLAKY, "每輪都 FAIL 但失敗原因不同：%s" % sorted(types)
        return STABLE_FAIL, "可穩定重現（%s）" % types.pop()
    if status == "SKIP":
        reasons = set((r["error_msg"] or "")[:60] for r in per_run)
        if len(reasons) > 1:
            return FLAKY, "每輪都 SKIP 但原因不同：%s" % sorted(reasons)
        return STABLE_SKIP, "原因一致"
    return FLAKY, "未知狀態 %s" % status


def _slow(durations):
    """回傳 (is_slow, reason)。只標記，不判 FAIL。"""
    if not durations:
        return False, ""
    avg = sum(durations) / len(durations)
    mx = max(durations)
    if mx >= 5.0 and avg > 0 and mx >= max(3 * avg, avg + 5):
        return True, "MAX %.2fs 遠高於 AVG %.2fs" % (mx, avg)
    return False, ""


def analyse(runs):
    """跨輪彙整。runs: [{mode, run, cases:{id:case}, ...}]"""
    all_ids = []
    for r in runs:
        for cid in r["cases"]:
            if cid not in all_ids:
                all_ids.append(cid)

    rows = []
    for cid in all_ids:
        per_run = []
        for r in runs:
            c = r["cases"].get(cid)
            if not c:
                continue
            per_run.append({
                "mode": r["mode"], "run": r["run"], "status": c["status"],
                "error_type": c.get("error_type") or "",
                "error_msg": c.get("error_msg") or "",
                "duration": float(c.get("duration_s") or 0),
                "group": c.get("group") or "", "name": c.get("name") or "",
            })
        klass, note = _classify(cid, per_run)
        durations = [p["duration"] for p in per_run]
        is_slow, slow_note = _slow(durations)
        rows.append({
            "case_id": cid,
            "group": per_run[0]["group"] if per_run else "",
            "name": per_run[0]["name"] if per_run else "",
            "runs_seen": len(per_run),
            "runs_total": len(runs),
            "pass": sum(1 for p in per_run if p["status"] == "PASS"),
            "fail": sum(1 for p in per_run if p["status"] == "FAIL"),
            "skip": sum(1 for p in per_run if p["status"] == "SKIP"),
            "consistency": ("%d/%d" % (
                max([sum(1 for p in per_run if p["status"] == s)
                     for s in ("PASS", "FAIL", "SKIP")] or [0]), len(per_run))
                if per_run else "0/0"),
            "classification": klass,
            "note": note,
            "avg_s": round(sum(durations) / len(durations), 2) if durations else 0,
            "min_s": round(min(durations), 2) if durations else 0,
            "max_s": round(max(durations), 2) if durations else 0,
            "slow": is_slow,
            "slow_note": slow_note,
            "per_run": per_run,
        })
    return rows


def write_reports(runs, rows, out_dir, run_id):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "stability_%s.csv" % run_id)
    json_path = os.path.join(out_dir, "stability_%s.json" % run_id)

    fields = ["mode", "run", "case_id", "group", "name", "status",
              "elapsed_s", "error_type", "error_msg", "classification"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            for p in row["per_run"]:
                w.writerow({
                    "mode": p["mode"], "run": p["run"], "case_id": row["case_id"],
                    "group": row["group"], "name": row["name"], "status": p["status"],
                    "elapsed_s": p["duration"], "error_type": p["error_type"],
                    "error_msg": p["error_msg"],
                    "classification": row["classification"],
                })

    counts = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1

    payload = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runs": [{k: v for k, v in r.items() if k != "cases"} for r in runs],
        "summary": {
            "total_runs": len(runs),
            "total_cases": len(rows),
            "classification": counts,
            "flaky": [r["case_id"] for r in rows if r["classification"] == FLAKY],
            "stable_fail": [r["case_id"] for r in rows if r["classification"] == STABLE_FAIL],
            "slow": [r["case_id"] for r in rows if r["slow"]],
        },
        "cases": rows,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return csv_path, json_path, counts


def report(runs, rows, counts, csv_path, json_path):
    line = "=" * 78
    print()
    print(line)
    print("Stability Summary")
    print(line)

    print("--- 每輪結果 ---")
    print("%-10s %-5s %-7s %-6s %-6s %-6s %-10s %s"
          % ("mode", "run", "total", "pass", "fail", "skip", "wall(s)", "safety"))
    for r in runs:
        s = r.get("summary") or {}
        print("%-10s %-5s %-7s %-6s %-6s %-6s %-10s %s"
              % (r["mode"], r["run"], s.get("TOTAL"), s.get("PASS"),
                 s.get("FAIL"), s.get("SKIP"), r["wall_seconds"],
                 r.get("safety", "?")))

    print()
    print("--- Case 穩定性分類 ---")
    for k in (STABLE_PASS, STABLE_FAIL, STABLE_SKIP, FLAKY, PARTIAL):
        if counts.get(k):
            print("  %-12s %d" % (k, counts[k]))

    stable_fail = [r for r in rows if r["classification"] == STABLE_FAIL]
    if stable_fail:
        print()
        print("--- STABLE FAIL（可穩定重現的缺陷，非 Flaky）---")
        for r in stable_fail:
            print("  [%s] %s  %s" % (r["case_id"], r["name"][:40], r["note"]))

    flaky = [r for r in rows if r["classification"] == FLAKY]
    print()
    if flaky:
        print("--- FLAKY ---")
        for r in flaky:
            print("  [%s] %s" % (r["case_id"], r["name"][:44]))
            print("      %s" % r["note"])
            for p in r["per_run"]:
                extra = (" %s: %s" % (p["error_type"], p["error_msg"][:70])) \
                    if p["status"] != "PASS" else ""
                print("      %s#%d %-5s %.2fs%s"
                      % (p["mode"], p["run"], p["status"], p["duration"], extra))
    else:
        print("--- FLAKY：無 ---")

    slow = [r for r in rows if r["slow"]]
    print()
    if slow:
        print("--- SLOW / POSSIBLE FLAKY（只標記，不判 FAIL）---")
        for r in sorted(slow, key=lambda x: -x["max_s"]):
            print("  [%-8s] %-38s AVG %6.2fs MIN %6.2fs MAX %6.2fs  %s"
                  % (r["case_id"], r["name"][:38], r["avg_s"], r["min_s"],
                     r["max_s"], r["slow_note"]))
    else:
        print("--- SLOW：無 ---")

    print()
    print("Stability CSV : %s" % csv_path)
    print("Stability JSON: %s" % json_path)
    return len(flaky)


def main(argv=None):
    config.force_utf8_stdout()
    ap = argparse.ArgumentParser(description="Stability / Flaky 驗證")
    ap.add_argument("--runs", type=int, default=3, help="每個模式跑幾輪（預設 3）")
    ap.add_argument("--modes", default="headed", help="headed / headless，逗號分隔")
    ap.add_argument("--flows", default=DEFAULT_FLOWS, help="要執行的 flow")
    args = ap.parse_args(argv)

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for m in modes:
        if m not in ("headed", "headless"):
            print("未知模式：%s" % m)
            return 2

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(str(config.OUTPUT_DIR), "stability")

    print("=" * 78)
    print("Stability Runner")
    print("=" * 78)
    print("模式     : %s" % modes)
    print("每模式輪數: %d（共 %d 次 Full Regression）" % (args.runs, args.runs * len(modes)))
    print("flows    : %s" % args.flows)
    print("報告目錄  : %s" % out_dir)

    runs = []
    for mode in modes:
        for i in range(1, args.runs + 1):
            info = _run_once(mode, args.flows, i, args.runs)
            data, cases = _load_cases(info["json_path"])
            info["cases"] = cases
            info["summary"] = (data or {}).get("summary") or info["printed_summary"]

            # 沿用既有 Safety Audit，不另建一套
            if info["json_path"] and os.path.exists(info["json_path"]):
                try:
                    audit = safety_audit.audit_file(info["json_path"])
                    info["safety"] = ("PASS(%d豁免)" % len(audit["exempted"])
                                      if not audit["violations"]
                                      else "FAIL(%d違規)" % len(audit["violations"]))
                    info["safety_violations"] = audit["violations"]
                except Exception as e:
                    info["safety"] = "ERROR"
                    info["safety_violations"] = [{"why": str(e)}]
            else:
                info["safety"] = "N/A"
                info["safety_violations"] = []
            runs.append(info)

    rows = analyse(runs)
    csv_path, json_path, counts = write_reports(runs, rows, out_dir, run_id)
    flaky_n = report(runs, rows, counts, csv_path, json_path)

    bad_safety = [r for r in runs if r.get("safety_violations")]
    if bad_safety:
        print()
        print("⚠ 有輪次的 Safety Audit 出現違規：%s"
              % [(r["mode"], r["run"]) for r in bad_safety])
    return 1 if (flaky_n or bad_safety) else 0


if __name__ == "__main__":
    sys.exit(main())
