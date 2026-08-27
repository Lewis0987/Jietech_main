# -*- coding: utf-8 -*-
"""把最新一份 Automation Summary 轉成 Markdown，供 GitHub Step Summary 顯示。

【設計原則】
    純讀取，不重跑測試、不修改 Reporter、不改任何結果。
    找不到 summary 時也要能輸出可讀訊息並回傳 0，
    以免 CI 的 summary step（if: always()）自己變成失敗原因。

用法：
    python tools/ci_summary.py >> $env:GITHUB_STEP_SUMMARY
"""

import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402


def _latest_summary():
    pattern = os.path.join(str(config.OUTPUT_DIR), "automation", "automation_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        return None, None
    path = files[-1]
    try:
        with open(path, encoding="utf-8") as f:
            return path, json.load(f)
    except Exception:
        return path, None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    path, data = _latest_summary()
    if not data:
        print("## Jietech Regression")
        print()
        print("找不到 Automation Summary（`test/output/automation/automation_*.json`）。")
        print("Regression 可能在產生 summary 之前就中斷了，請查看 Artifact 內的 log 與 result。")
        if path:
            print()
            print("讀取失敗的檔案：`%s`" % os.path.basename(path))
        return 0

    meta = data.get("meta", {})
    raw = data.get("raw_result", {})
    comp = data.get("comparison", {})
    safety = data.get("safety", {})
    dl = data.get("download", {})

    final = data.get("final_status", "?")
    code = data.get("exit_code", "?")
    icon = "✅" if code == 0 else "❌"

    print("## %s Jietech Regression — %s" % (icon, final))
    print()
    print("| 項目 | 值 |")
    print("|---|---|")
    print("| Exit Code | `%s` |" % code)
    print("| 模式 | %s |" % meta.get("mode", "?"))
    print("| 耗時 | %s s |" % meta.get("duration_s", "?"))
    print("| Baseline | `%s` |" % os.path.basename(meta.get("baseline_file", "") or "?"))
    print()

    print("### Raw Result（原始事實，未經修改）")
    print()
    print("| Total | PASS | FAIL | SKIP |")
    print("|---|---|---|---|")
    print("| %s | %s | %s | %s |" % (raw.get("TOTAL"), raw.get("PASS"),
                                     raw.get("FAIL"), raw.get("SKIP")))
    print()
    print("> `FAIL` 不為 0 屬預期 —— `C-00` / `I-00` 是已知網站缺陷（Known Stable Fail）。")
    print("> CI 判定依據是 Baseline 比對後的 Exit Code，不是 raw FAIL 數量。")
    print()

    print("### Baseline Comparison")
    print()
    print("| 分類 | 數量 |")
    print("|---|---|")
    for k in sorted(comp):
        print("| %s | %s |" % (k, comp[k]))
    print()

    def _list(key, title, warn=False):
        items = data.get(key) or []
        if not items:
            return
        mark = "⚠️ " if warn else ""
        print("### %s%s" % (mark, title))
        print()
        for cid in items:
            row = next((r for r in data.get("cases", []) if r.get("case_id") == cid), {})
            print("- **%s** %s — expected `%s`, actual `%s`"
                  % (cid, row.get("name", ""), row.get("expected", "?"), row.get("actual", "?")))
            if row.get("error_msg"):
                print("  - `%s`: %s" % (row.get("error_type", ""), row["error_msg"][:200]))
            if row.get("screenshot"):
                print("  - screenshot: `%s`" % os.path.basename(row["screenshot"]))
        print()

    _list("new_fail", "NEW FAIL（新的 Regression）", warn=True)
    _list("missing_case", "MISSING CASE", warn=True)
    _list("new_skip", "NEW SKIP（覆蓋率下降）", warn=True)
    _list("recovered", "RECOVERED（Known Fail 已恢復）", warn=True)
    _list("new_case", "NEW CASE", warn=True)

    if data.get("recovered"):
        print("> Known Fail 已恢復，**Baseline 可能需要人工確認更新**。")
        print("> 自動化不會、也不允許自動改寫 Baseline。")
        print()

    known = [r["case_id"] for r in data.get("cases", [])
             if r.get("classification") == "EXPECTED FAIL"]
    if known:
        print("### Known Stable Fail（符合 Baseline，不算新 Regression）")
        print()
        print("`%s`" % "`, `".join(known))
        print()

    print("### Safety Audit / Download")
    print()
    print("| 項目 | 值 |")
    print("|---|---|")
    print("| Safety Audit | **%s** |" % safety.get("result", "?"))
    print("| 違規數 | %s |" % safety.get("violations", "?"))
    print("| 語意豁免 | %s |" % safety.get("exempted", "?"))
    print("| Download 殘留 | %s |" % dl.get("count", "?"))
    print()

    for v in (safety.get("violation_detail") or [])[:5]:
        print("- ⚠️ **%s** `%s` → %s" % (v.get("case", "?"),
                                          (v.get("action") or "")[:80],
                                          v.get("why", "")))
    print()
    print("_Summary 來源：`%s`_" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
