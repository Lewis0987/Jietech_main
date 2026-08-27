# -*- coding: utf-8 -*-
"""test/output/ 測試產物保留清理（Output Retention 方案 A）。

【預設不刪除任何檔案】
    直接執行 = dry-run，只列出計畫。
    只有明確加上 --apply 才會真的刪除。

保留規則：
    result_<ts>.csv / result_<ts>.json     保留最近 20 次 execution
    screenshots/FAIL_*.png                 與所屬 execution 關聯處理（見下）
    probe/snapshot_<name>_<ts>.json        每個 name 保留最近 3 份
    probe/probe_<ts>.json                  保留最近 5 份
    probe/deep_<ts>.json                   保留最近 5 份

截圖關聯方式：
    截圖檔名只有 HHMMSS、沒有日期，因此**不從檔名推測**歸屬。
    改為讀取每個 result JSON 的 `screenshot` 欄位取得確切路徑：
      * 被保留的 execution 引用      -> KEEP
      * 只被刪除的 execution 引用    -> DELETE
      * 沒有任何 result 引用到       -> KEEP（無法可靠關聯，寧可保留）
    因此不會出現「保留下來的 CSV/JSON 指向已被刪除的截圖」。

安全守門：
    * 所有路徑 resolve 後必須仍位於 test/output/ 之內
    * 禁止 .. 路徑逃逸
    * 禁止 symlink（含指向 output 之外者）
    * 不符合既定命名規則者一律標記 UNKNOWN，永遠不刪
    * dry-run 與 --apply 使用完全相同的 selection logic（build_plan）
    * 單一刪除失敗不會中止其他項目，但最終 exit code 會反映失敗

用法：
    python -m tools.cleanup_output              # dry-run（預設）
    python -m tools.cleanup_output --apply      # 真的刪除
    python -m tools.cleanup_output --keep-results 30 --keep-snapshots 5
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402

# ---------------------------------------------------------------- 保留數量預設
KEEP_RESULTS = 20        # 最近 N 次 execution 的 result CSV / JSON
KEEP_SNAPSHOTS = 3       # 每個 snapshot name 保留最近 N 份
KEEP_PROBES = 5          # probe_<ts>.json
KEEP_DEEPS = 5           # deep_<ts>.json
# 自動 Regression 的 Summary 與 log：保留較久，且「有新 Regression 的那幾份」永遠保留
KEEP_AUTOMATION = 30

# ---------------------------------------------------------------- 命名規則
TS = r"(\d{8}_\d{6})"
RE_RESULT = re.compile(r"^result_%s\.(csv|json)$" % TS)
RE_SNAPSHOT = re.compile(r"^snapshot_(.+)_%s\.json$" % TS)
RE_PROBE = re.compile(r"^probe_%s\.json$" % TS)
RE_DEEP = re.compile(r"^deep_%s\.json$" % TS)
RE_SHOT = re.compile(r"^FAIL_.+_\d{6}\.png$")
RE_STABILITY = re.compile(r"^stability_%s\.(csv|json)$" % TS)
RE_AUTOMATION = re.compile(r"^automation_%s\.(csv|json)$" % TS)
RE_AUTO_LOG = re.compile(r"^scheduled_%s\.log$" % TS)

# 已知但不屬於測試產物、也不該刪的檔案
PROTECTED_NAMES = {".gitignore"}

KEEP, DELETE, UNKNOWN = "KEEP", "DELETE", "UNKNOWN"


class Item(object):
    __slots__ = ("path", "category", "stamp", "size", "decision", "reason")

    def __init__(self, path, category, stamp, size, decision, reason):
        self.path = path
        self.category = category
        self.stamp = stamp
        self.size = size
        self.decision = decision
        self.reason = reason


# ================================================================ 安全守門
def _safe_under(root, path):
    """resolve 後仍必須位於 root 之內，且不得是 symlink。

    回傳 (ok, reason)。
    """
    try:
        if os.path.islink(path):
            return False, "是 symlink，基於安全不處理"
        real_root = os.path.realpath(root)
        real_path = os.path.realpath(path)
        if real_path == real_root:
            return False, "指向 output 根目錄本身"
        prefix = real_root + os.sep
        if not real_path.startswith(prefix):
            return False, "resolve 後不在 test/output/ 之內（可能為路徑逃逸）"
        if ".." in os.path.relpath(real_path, real_root).split(os.sep):
            return False, "路徑含 .. 逃逸"
        return True, ""
    except Exception as e:
        return False, "路徑檢查失敗：%s" % e


def _stat(path):
    try:
        st = os.stat(path)
        return st.st_size, st.st_mtime
    except OSError:
        return 0, 0.0


def _fmt_ts(stamp, mtime):
    if stamp:
        try:
            return datetime.strptime(stamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    if mtime:
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S") + " (mtime)"
    return "-"


def _human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.2f %s" % (n, unit)
        n /= 1024.0


# ================================================================ 掃描
def _walk(root):
    """回傳 output/ 底下所有檔案的絕對路徑。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 不跟隨 symlink 目錄
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            out.append(os.path.join(dirpath, name))
    return out


def _classify(root, path):
    """回傳 (category, stamp, extra)；不符合命名規則者 category=None。"""
    name = os.path.basename(path)
    rel_dir = os.path.relpath(os.path.dirname(path), root).replace("\\", "/")

    if name in PROTECTED_NAMES:
        return "protected", None, None

    if rel_dir == ".":
        m = RE_RESULT.match(name)
        if m:
            return "result", m.group(1), m.group(2)
        return None, None, None

    if rel_dir == "automation":
        m = RE_AUTOMATION.match(name)
        if m:
            return "automation", m.group(1), None
        return None, None, None

    if rel_dir == "automation/logs":
        m = RE_AUTO_LOG.match(name)
        if m:
            return "automation_log", m.group(1), None
        return None, None, None

    if rel_dir == "stability":
        # Stability 證據一律保留，不設刪除規則
        if RE_STABILITY.match(name):
            return "stability", None, None
        return None, None, None

    if rel_dir == "screenshots":
        if RE_SHOT.match(name):
            return "screenshot", None, None
        return None, None, None

    if rel_dir == "probe":
        m = RE_SNAPSHOT.match(name)
        if m:
            return "snapshot", m.group(2), m.group(1)
        m = RE_PROBE.match(name)
        if m:
            return "probe", m.group(1), None
        m = RE_DEEP.match(name)
        if m:
            return "deep", m.group(1), None
        return None, None, None

    return None, None, None


def _referenced_screenshots(json_path, root):
    """讀取 result JSON 內所有 screenshot 欄位，回傳位於 output/ 內的 realpath 集合。"""
    refs = set()
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None                      # 讀不到 -> 無法可靠關聯
    for case in data.get("cases", []) or []:
        shot = (case.get("screenshot") or "").strip()
        if not shot:
            continue
        ok, _ = _safe_under(root, shot)
        if ok:
            refs.add(os.path.realpath(shot))
    return refs


# ================================================================ 計畫
def build_plan(root, keep_results=KEEP_RESULTS, keep_snapshots=KEEP_SNAPSHOTS,
               keep_probes=KEEP_PROBES, keep_deeps=KEEP_DEEPS):
    """產生清理計畫。dry-run 與 --apply 共用這一份邏輯。"""
    items = []
    buckets = {"result": {}, "snapshot": {}, "probe": [], "deep": [],
               "screenshot": [], "automation": [], "automation_log": []}
    unsafe = []

    for path in _walk(root):
        ok, why = _safe_under(root, path)
        if not ok:
            size, mtime = _stat(path)
            items.append(Item(path, "unsafe", None, size, UNKNOWN, why))
            unsafe.append(path)
            continue

        category, stamp, extra = _classify(root, path)
        size, mtime = _stat(path)

        if category is None:
            items.append(Item(path, "unknown", None, size, UNKNOWN,
                              "不符合任何既定命名規則，不處理"))
            continue
        if category == "protected":
            items.append(Item(path, "protected", None, size, KEEP,
                              "受保護檔案，不處理"))
            continue
        if category == "stability":
            items.append(Item(path, "stability", None, size, KEEP,
                              "Stability 驗證證據，一律保留不刪除"))
            continue

        if category == "result":
            buckets["result"].setdefault(stamp, []).append((path, size, extra))
        elif category == "snapshot":
            buckets["snapshot"].setdefault(extra, []).append((path, size, stamp))
        elif category in ("probe", "deep", "automation", "automation_log"):
            buckets.setdefault(category, []).append((path, size, stamp))
        elif category == "screenshot":
            buckets["screenshot"].append((path, size, mtime))

    # ---------------- result：保留最近 N 次 execution ----------------
    run_ids = sorted(buckets["result"].keys(), reverse=True)
    keep_runs = set(run_ids[:keep_results])
    drop_runs = set(run_ids[keep_results:])

    for run_id in run_ids:
        kept = run_id in keep_runs
        for path, size, ext in buckets["result"][run_id]:
            if kept:
                items.append(Item(path, "result", run_id, size, KEEP,
                                  "最近 %d 次 execution 之內" % keep_results))
            else:
                items.append(Item(path, "result", run_id, size, DELETE,
                                  "超出最近 %d 次 execution（第 %d 舊）"
                                  % (keep_results, run_ids.index(run_id) + 1)))

    # ---------------- screenshot：只靠 result JSON 的實際引用 ----------------
    kept_refs, dropped_refs = set(), set()
    unreadable_runs = []
    for run_id in run_ids:
        json_path = None
        for path, _size, ext in buckets["result"][run_id]:
            if ext == "json":
                json_path = path
        if json_path is None:
            unreadable_runs.append(run_id)
            continue
        refs = _referenced_screenshots(json_path, root)
        if refs is None:
            unreadable_runs.append(run_id)
            continue
        (kept_refs if run_id in keep_runs else dropped_refs).update(refs)

    for path, size, mtime in buckets["screenshot"]:
        real = os.path.realpath(path)
        if real in kept_refs:
            items.append(Item(path, "screenshot", None, size, KEEP,
                              "被保留的 result execution 引用"))
        elif real in dropped_refs:
            items.append(Item(path, "screenshot", None, size, DELETE,
                              "僅被將刪除的 result execution 引用"))
        else:
            items.append(Item(path, "screenshot", None, size, KEEP,
                              "沒有任何 result 引用到，無法可靠關聯 -> 保留"))

    # ---------------- snapshot：每個 name 保留最近 N 份 ----------------
    for name, rows in sorted(buckets["snapshot"].items()):
        rows.sort(key=lambda r: r[2], reverse=True)
        for idx, (path, size, stamp) in enumerate(rows):
            if idx < keep_snapshots:
                items.append(Item(path, "snapshot", stamp, size, KEEP,
                                  "name=%s 最近 %d 份之內（第 %d 新）"
                                  % (name, keep_snapshots, idx + 1)))
            else:
                items.append(Item(path, "snapshot", stamp, size, DELETE,
                                  "name=%s 超出最近 %d 份（第 %d 新）"
                                  % (name, keep_snapshots, idx + 1)))

    # ---------------- automation：有新 Regression 的永遠保留 ----------------
    failed_stamps = set()
    for path, _size, stamp in buckets.get("automation", []):
        if not path.lower().endswith(".json"):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("exit_code") not in (0, None) or data.get("new_fail"):
                failed_stamps.add(stamp)
        except Exception:
            failed_stamps.add(stamp)      # 讀不到就保守保留

    for cat in ("automation", "automation_log"):
        rows = buckets.get(cat, [])
        rows.sort(key=lambda r: r[2], reverse=True)
        for idx, (path, size, stamp) in enumerate(rows):
            if stamp in failed_stamps:
                items.append(Item(path, cat, stamp, size, KEEP,
                                  "此次自動 Regression 有新 Regression / 異常，永久保留"))
            elif idx < KEEP_AUTOMATION:
                items.append(Item(path, cat, stamp, size, KEEP,
                                  "最近 %d 份之內（第 %d 新）" % (KEEP_AUTOMATION, idx + 1)))
            else:
                items.append(Item(path, cat, stamp, size, DELETE,
                                  "超出最近 %d 份（第 %d 新）" % (KEEP_AUTOMATION, idx + 1)))

    # ---------------- probe / deep ----------------
    for cat, keep_n in (("probe", keep_probes), ("deep", keep_deeps)):
        rows = buckets[cat]
        rows.sort(key=lambda r: r[2], reverse=True)
        for idx, (path, size, stamp) in enumerate(rows):
            if idx < keep_n:
                items.append(Item(path, cat, stamp, size, KEEP,
                                  "最近 %d 份之內（第 %d 新）" % (keep_n, idx + 1)))
            else:
                items.append(Item(path, cat, stamp, size, DELETE,
                                  "超出最近 %d 份（第 %d 新）" % (keep_n, idx + 1)))

    meta = {"run_ids": run_ids, "keep_runs": sorted(keep_runs, reverse=True),
            "drop_runs": sorted(drop_runs, reverse=True),
            "unreadable_runs": unreadable_runs, "unsafe": unsafe}
    return items, meta


# ================================================================ 輸出
def report(items, meta, root, apply_mode):
    line = "=" * 78
    print(line)
    print("Output Retention 清理%s" % ("（--apply：實際刪除）" if apply_mode else "（dry-run：不會刪除任何檔案）"))
    print(line)
    print("目標目錄 : %s" % root)
    print("execution: 共 %d 次，保留 %d 次，超出 %d 次"
          % (len(meta["run_ids"]), len(meta["keep_runs"]), len(meta["drop_runs"])))
    if meta["unreadable_runs"]:
        print("           ⚠ %d 次 execution 的 JSON 無法讀取，其截圖一律保留：%s"
              % (len(meta["unreadable_runs"]), meta["unreadable_runs"][:5]))
    if meta["unsafe"]:
        print("           ⚠ %d 個路徑未通過安全檢查，標記 UNKNOWN" % len(meta["unsafe"]))

    to_delete = [i for i in items if i.decision == DELETE]
    if to_delete:
        print()
        print("--- 將刪除的檔案 ---")
        print("%-10s %-21s %10s  %s" % ("類型", "timestamp", "大小", "路徑 / 原因"))
        for i in sorted(to_delete, key=lambda x: (x.category, x.path)):
            _size, mtime = _stat(i.path)
            print("%-10s %-21s %10s  %s"
                  % (i.category, _fmt_ts(i.stamp, mtime), _human(i.size), i.path))
            print("%-10s %-21s %10s  └─ %s" % ("", "", "", i.reason))
    else:
        print()
        print("--- 沒有任何檔案符合刪除條件 ---")

    unknown = [i for i in items if i.decision == UNKNOWN]
    if unknown:
        print()
        print("--- UNKNOWN（永遠不刪）---")
        for i in unknown:
            print("  %s" % i.path)
            print("    └─ %s" % i.reason)

    keep_n = len([i for i in items if i.decision == KEEP])
    del_n = len(to_delete)
    unk_n = len(unknown)
    free = sum(i.size for i in to_delete)

    print()
    print(line)
    print("Summary")
    print(line)
    print("KEEP    : %d 個檔案" % keep_n)
    print("DELETE  : %d 個檔案" % del_n)
    print("UNKNOWN : %d 個檔案" % unk_n)
    print("預計釋放空間 : %s" % _human(free))
    print("目前總計     : %d 個檔案 / %s"
          % (len(items), _human(sum(i.size for i in items))))
    return del_n, free


def do_delete(items, root):
    """實際刪除；單一失敗不中止其他項目。回傳 (deleted, failed)。"""
    deleted, failed = [], []
    for i in items:
        if i.decision != DELETE:
            continue
        ok, why = _safe_under(root, i.path)      # 刪除前再檢查一次
        if not ok:
            failed.append((i.path, "刪除前安全檢查未通過：%s" % why))
            continue
        try:
            os.remove(i.path)
            deleted.append(i.path)
            print("  已刪除 %s" % i.path)
        except FileNotFoundError:
            deleted.append(i.path)
        except Exception as e:
            failed.append((i.path, str(e)))
            print("  刪除失敗 %s：%s" % (i.path, e))
    return deleted, failed


# ================================================================ main
def main(argv=None):
    config.force_utf8_stdout()

    ap = argparse.ArgumentParser(
        description="test/output/ 測試產物保留清理（預設 dry-run，不刪除）")
    ap.add_argument("--apply", action="store_true",
                    help="真的執行刪除；未加此參數一律只列出計畫")
    ap.add_argument("--keep-results", type=int, default=KEEP_RESULTS,
                    help="result CSV/JSON 保留最近幾次 execution（預設 %d）" % KEEP_RESULTS)
    ap.add_argument("--keep-snapshots", type=int, default=KEEP_SNAPSHOTS,
                    help="每個 snapshot name 保留幾份（預設 %d）" % KEEP_SNAPSHOTS)
    ap.add_argument("--keep-probes", type=int, default=KEEP_PROBES,
                    help="probe_<ts>.json 保留幾份（預設 %d）" % KEEP_PROBES)
    ap.add_argument("--keep-deeps", type=int, default=KEEP_DEEPS,
                    help="deep_<ts>.json 保留幾份（預設 %d）" % KEEP_DEEPS)
    args = ap.parse_args(argv)

    for n in (args.keep_results, args.keep_snapshots, args.keep_probes, args.keep_deeps):
        if n < 1:
            print("保留數量必須 >= 1")
            return 2

    root = os.path.realpath(str(config.OUTPUT_DIR))
    if not os.path.isdir(root):
        print("找不到 output 目錄：%s" % root)
        return 2

    # dry-run 與 --apply 使用完全相同的 selection logic
    items, meta = build_plan(root,
                             keep_results=args.keep_results,
                             keep_snapshots=args.keep_snapshots,
                             keep_probes=args.keep_probes,
                             keep_deeps=args.keep_deeps)
    del_n, free = report(items, meta, root, args.apply)

    if not args.apply:
        print()
        print("dry-run：未刪除任何檔案。確認無誤後加上 --apply 才會實際刪除。")
        return 0

    if del_n == 0:
        print()
        print("沒有需要刪除的檔案。")
        return 0

    print()
    print("--- 執行刪除 ---")
    deleted, failed = do_delete(items, root)
    print()
    print("實際刪除 : %d 個" % len(deleted))
    print("刪除失敗 : %d 個" % len(failed))
    for path, why in failed:
        print("  %s -> %s" % (path, why))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
