# -*- coding: utf-8 -*-
"""下載監控 / 驗證 / 清理。

流程（第五階段要求）：
    1. snapshot(download_path)          下載前快照
    2. 點 Download                       （由 flow 負責）
    3. wait_for_new_download(...)        只找「本次新增」的檔案
    4. .crdownload / .tmp / .partial 不算完成
    5. 確認 APK 完成（檔案大小穩定 + 無對應暫存檔）
    6. delete_downloads(...)             只刪除本次下載的檔案
    7. assert_deleted(...)               確認刪除成功

安全保證：一切以 before/after 差集為準，
絕不會碰到 Downloads 資料夾裡原本就存在的檔案。

已知問題對策：
    Chrome 實際下載位置與 Python 監控位置不同 -> 逾時時呼叫
    diagnose(...) 掃描其他候選資料夾，把「靜默 Timeout」變成可診斷的訊息。
"""

import os
import time
from pathlib import Path

PARTIAL_SUFFIXES = (".crdownload", ".tmp", ".partial")


# ------------------------------------------------------------------ 基本
def snapshot(download_path):
    """下載前快照：回傳目前資料夾內的檔名集合。"""
    p = Path(download_path)
    p.mkdir(parents=True, exist_ok=True)
    try:
        return set(os.listdir(str(p)))
    except OSError:
        return set()


def is_partial(name):
    lower = name.lower()
    return any(lower.endswith(s) for s in PARTIAL_SUFFIXES)


def _match_ext(name, extensions):
    if not extensions:
        return not is_partial(name)
    lower = name.lower()
    return any(lower.endswith(e.lower()) for e in extensions)


def _size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


# ------------------------------------------------------------------ 等待
def wait_for_new_download(download_path, before, timeout=60, extensions=(".apk",),
                          poll=0.5, stable_checks=2, log=None):
    """等待「本次新增」且已完成的下載檔。

    回傳 dict:
        {"ok": bool, "files": [檔名], "pending": [未完成檔名],
         "elapsed": 秒, "reason": str}
    不拋例外，由呼叫端的 case 決定 PASS/FAIL。
    """
    log = log or (lambda *_a, **_k: None)
    path = Path(download_path)
    path.mkdir(parents=True, exist_ok=True)
    before = set(before or ())
    start = time.time()
    sizes = {}
    stable = {}
    pending = []

    while time.time() - start < timeout:
        try:
            after = set(os.listdir(str(path)))
        except OSError:
            after = set()
        new_files = after - before

        pending = sorted(f for f in new_files if is_partial(f))
        candidates = sorted(f for f in new_files if not is_partial(f) and _match_ext(f, extensions))

        done = []
        for name in candidates:
            full = str(path / name)
            # 仍有對應的暫存檔 -> 尚未完成
            if any((name + s) in new_files for s in PARTIAL_SUFFIXES):
                continue
            size = _size(full)
            if size <= 0:
                stable[name] = 0
                sizes[name] = size
                continue
            if sizes.get(name) == size:
                stable[name] = stable.get(name, 0) + 1
            else:
                stable[name] = 0
            sizes[name] = size
            if stable[name] >= stable_checks:
                done.append(name)

        if done:
            elapsed = round(time.time() - start, 2)
            log("下載完成：%s（%.2fs）" % (done, elapsed))
            return {"ok": True, "files": done, "pending": pending,
                    "elapsed": elapsed, "reason": ""}

        if pending:
            log("下載中：%s" % pending)
        time.sleep(poll)

    elapsed = round(time.time() - start, 2)
    reason = "逾時 %ss 未偵測到完成的下載檔（副檔名 %s）" % (timeout, list(extensions))
    if pending:
        reason += "；仍在下載中：%s" % pending
    return {"ok": False, "files": [], "pending": pending,
            "elapsed": elapsed, "reason": reason}


# ------------------------------------------------------------------ 清理
def delete_downloads(download_path, files, retries=5, delay=1.0, log=None):
    """只刪除本次下載產生的檔案。回傳 (deleted, failed)。"""
    log = log or (lambda *_a, **_k: None)
    path = Path(download_path)
    deleted, failed = [], []
    for name in files:
        full = path / name
        for attempt in range(retries):
            try:
                os.remove(str(full))
                deleted.append(name)
                log("已刪除：%s" % name)
                break
            except FileNotFoundError:
                deleted.append(name)      # 已不存在，視為已清理
                break
            except PermissionError:
                if attempt == retries - 1:
                    failed.append(name)
                    log("檔案被占用，無法刪除：%s" % name)
                else:
                    time.sleep(delay)
            except OSError as e:
                failed.append(name)
                log("刪除失敗 %s：%s" % (name, e))
                break
    return deleted, failed


def assert_deleted(download_path, files):
    """回傳仍然存在的檔案清單（空 list 代表刪除驗證通過）。"""
    path = Path(download_path)
    return [f for f in files if (path / f).exists()]


def cleanup_partials(download_path, before, log=None):
    """清掉本次產生但沒下載完的暫存檔（只針對 before 之後新增的）。"""
    log = log or (lambda *_a, **_k: None)
    path = Path(download_path)
    try:
        new_files = set(os.listdir(str(path))) - set(before or ())
    except OSError:
        return []
    removed = []
    for name in sorted(f for f in new_files if is_partial(f)):
        try:
            os.remove(str(path / name))
            removed.append(name)
            log("已清除暫存檔：%s" % name)
        except OSError:
            pass
    return removed


# ------------------------------------------------------------------ 診斷
def candidate_dirs(configured_path):
    """列出可能的下載資料夾，用於「檔案下載成功但監控不到」的診斷。"""
    dirs = [Path(configured_path)]
    dirs.append(Path.home() / "Downloads")
    up = os.environ.get("USERPROFILE")
    if up:
        dirs.append(Path(up) / "Downloads")
    dirs.append(Path.cwd())

    # Windows 使用者可能把「下載」重新導向到別的磁碟
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        value, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
        if value:
            dirs.append(Path(value))
    except Exception:
        pass

    seen, out = set(), []
    for d in dirs:
        try:
            resolved = d.resolve()
        except Exception:
            continue
        if str(resolved).lower() in seen:
            continue
        seen.add(str(resolved).lower())
        out.append(resolved)
    return out


def diagnose(configured_path, before, extensions=(".apk",), window_seconds=180):
    """下載逾時後呼叫：找出檔案到底掉到哪個資料夾。

    回傳 list[dict]：{"dir":..., "files":[...] , "same_as_configured": bool}
    """
    cutoff = time.time() - window_seconds
    before = set(before or ())
    configured = str(Path(configured_path).resolve()).lower()
    findings = []

    for d in candidate_dirs(configured_path):
        try:
            names = os.listdir(str(d))
        except OSError:
            continue
        same = str(d).lower() == configured
        hits = []
        for name in names:
            if same and name in before:
                continue
            if not _match_ext(name, extensions) and not is_partial(name):
                continue
            try:
                if os.path.getmtime(str(d / name)) < cutoff:
                    continue
            except OSError:
                continue
            hits.append(name)
        if hits:
            findings.append({"dir": str(d), "files": sorted(hits),
                             "same_as_configured": same})
    return findings


def describe(download_path):
    """給報告 meta 用的一行說明。"""
    p = Path(download_path)
    try:
        n = len(os.listdir(str(p)))
    except OSError:
        n = -1
    return "%s (exists=%s, files=%s)" % (p, p.exists(), n)
