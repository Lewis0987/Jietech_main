# -*- coding: utf-8 -*-
"""測試結果收集 / 輸出（Terminal + CSV + JSON + 截圖）。

用法：
    reporter = Reporter(title="IN V6 FULL SITE AUTOMATION TEST")
    reporter.attach_driver(driver)
    reporter.set_recovery(lambda: recovery.go_home(driver, home_url))

    reporter.group("B", "Header")
    with reporter.case("B-1-1", "Header_download") as c:
        c.found("找到 Download 按鈕")
        c.action("點擊 Download")
        c.check("APK 下載完成")

單一 case 失敗只會記錄 FAIL + 截圖 + recovery，絕不中斷整體流程。
"""

import csv
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

# 輸出被導向檔案 / pipe 時關閉 ANSI，避免 log 檔出現亂碼控制字元
_USE_COLOR = bool(getattr(sys.stdout, "isatty", lambda: False)()) and os.environ.get("NO_COLOR") is None

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

_C = {
    "reset": "\033[0m",
    "green": "\033[32m",
    "red": "\033[91m",
    "yellow": "\033[33m",
    "blue": "\033[94m",
    "grey": "\033[90m",
    "bold": "\033[1m",
}


def _c(text, color):
    if not _USE_COLOR:
        return str(text)
    return "%s%s%s" % (_C.get(color, ""), text, _C["reset"])


class SkipCase(Exception):
    """由 case 內部主動拋出，將該 case 標記為 SKIP（非失敗）。"""


# 瀏覽器 / driver 已經死掉的徵兆。一旦出現，後續 case 全都是雜訊，
# 而且截圖與 recovery 也會跟著卡住（實測曾讓單一 case 卡住 31 分鐘）。
DEAD_SESSION_MARKERS = (
    "invalid session id",
    "session deleted",
    "no such window",
    "chrome not reachable",
    "not connected to devtools",
    "target window already closed",
    "browser has closed the connection",
    "unable to connect to renderer",
)


def is_dead_session(exc):
    msg = str(exc).lower()
    return any(m in msg for m in DEAD_SESSION_MARKERS)


class CaseContext:
    """單一 case 的執行情境；提供 found / action / check / note / skip。"""

    def __init__(self, case_id, name, group):
        self.case_id = case_id
        self.name = name
        self.group = group
        self.steps = []

    def step(self, message):
        """記錄一個已完成的驗證步驟。"""
        self.steps.append(str(message))
        print("   %s %s" % (_c("-", "grey"), message))
        return self

    # 同義詞，讓 flow 讀起來貼近 Found -> Action -> Post-condition
    def found(self, message):
        return self.step("[found] %s" % message)

    def action(self, message):
        return self.step("[action] %s" % message)

    def check(self, message):
        return self.step("[check] %s" % message)

    def note(self, message):
        self.steps.append("(note) %s" % message)
        print("   %s" % _c("- " + str(message), "grey"))
        return self

    def skip(self, reason):
        raise SkipCase(reason)


class Result:
    __slots__ = ("timestamp", "group", "case_id", "name", "status",
                 "duration_s", "error_type", "error_msg", "screenshot", "steps")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def as_dict(self):
        return dict((k, getattr(self, k)) for k in self.__slots__)


class Reporter:
    CSV_FIELDS = ["timestamp", "group", "case_id", "name", "status",
                  "duration_s", "error_type", "error_msg", "screenshot", "steps"]

    def __init__(self, title="FULL SITE AUTOMATION TEST",
                 output_dir=None, screenshot_dir=None, run_id=None):
        self.title = title
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent / "output"
        self.output_dir = Path(base)
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else self.output_dir / "screenshots"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.results = []
        self.session_dead = False
        self._driver = None
        self._recovery = None
        self._current_group = "-"
        self._started = time.time()
        self.meta = {}

    # ------------------------------------------------------------ 設定
    def attach_driver(self, driver):
        self._driver = driver

    def set_recovery(self, fn):
        """fn() 會在每個 FAIL 之後被呼叫，用來把頁面帶回穩定狀態。"""
        self._recovery = fn

    def set_meta(self, **kw):
        self.meta.update(kw)

    # ------------------------------------------------------------ 輸出
    def header(self):
        line = "=" * 60
        print(line)
        print(_c(self.title, "bold"))
        for k, v in self.meta.items():
            print("%-14s: %s" % (k, v))
        print(line)

    def group(self, letter, title):
        self._current_group = letter
        print()
        print(_c("[%s] %s" % (letter, title), "bold"))

    # ------------------------------------------------------------ case
    @contextmanager
    def case(self, case_id, name):
        ctx = CaseContext(case_id, name, self._current_group)
        started = time.time()
        ts = datetime.now().isoformat(timespec="seconds")
        status, err_type, err_msg, shot = PASS, "", "", ""

        try:
            yield ctx
        except SkipCase as e:
            status, err_type, err_msg = SKIP, "SkipCase", str(e)
        except KeyboardInterrupt:
            raise
        except BaseException as e:                 # noqa: BLE001 - 刻意攔截全部，維持流程不中斷
            status = FAIL
            err_type = type(e).__name__
            err_msg = self._clean(e)
            if is_dead_session(e):
                # 瀏覽器已死：截圖與 recovery 只會一起卡住，直接標記讓上層中止
                self.session_dead = True
                err_msg = "[SESSION DEAD] " + err_msg
            else:
                shot = self._screenshot(case_id)
                self._run_recovery()
        finally:
            duration = round(time.time() - started, 2)
            self.results.append(Result(
                timestamp=ts, group=ctx.group, case_id=case_id, name=name,
                status=status, duration_s=duration, error_type=err_type,
                error_msg=err_msg, screenshot=shot,
                steps=" | ".join(ctx.steps),
            ))
            self._print_case(case_id, name, status, duration, err_type, err_msg, shot)

    # ------------------------------------------------------------ 內部
    @staticmethod
    def _clean(exc):
        """只保留 Stacktrace 之前的訊息，避免 terminal 被洗版。"""
        msg = str(exc).split("Stacktrace")[0].strip()
        if not msg:
            msg = repr(exc)
        return " ".join(msg.split())[:500]

    def _screenshot(self, case_id):
        if self._driver is None or self.session_dead:
            return ""
        safe_id = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(case_id))
        path = self.screenshot_dir / ("FAIL_%s_%s.png" % (safe_id, datetime.now().strftime("%H%M%S")))
        try:
            self._driver.save_screenshot(str(path))
            return str(path)
        except Exception:
            return ""

    def _run_recovery(self):
        if self._recovery is None or self.session_dead:
            return
        try:
            self._recovery()
        except Exception as e:
            print("   %s" % _c("recovery 失敗：" + self._clean(e), "yellow"))

    def _print_case(self, case_id, name, status, duration, err_type, err_msg, shot):
        if status == PASS:
            icon, color = "PASS", "green"
        elif status == FAIL:
            icon, color = "FAIL", "red"
        else:
            icon, color = "SKIP", "yellow"
        print("%s %s %s %s" % (_c(icon, color), case_id, name, _c("(%ss)" % duration, "grey")))
        if status == FAIL:
            print("   %s" % _c("Error      : %s: %s" % (err_type, err_msg), "red"))
            if shot:
                print("   %s" % _c("Screenshot : %s" % shot, "red"))
        elif status == SKIP and err_msg:
            print("   %s" % _c("Reason     : %s" % err_msg, "yellow"))

    # ------------------------------------------------------------ 統計
    def counts(self):
        c = {PASS: 0, FAIL: 0, SKIP: 0}
        for r in self.results:
            c[r.status] = c.get(r.status, 0) + 1
        c["TOTAL"] = len(self.results)
        return c

    def overall(self):
        return FAIL if self.counts()[FAIL] else PASS

    # ------------------------------------------------------------ 落檔
    def write_csv(self):
        path = self.output_dir / ("result_%s.csv" % self.run_id)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
            w.writeheader()
            for r in self.results:
                w.writerow(r.as_dict())
        return path

    def write_json(self):
        path = self.output_dir / ("result_%s.json" % self.run_id)
        payload = {
            "title": self.title,
            "run_id": self.run_id,
            "meta": self.meta,
            "started_at": datetime.fromtimestamp(self._started).isoformat(timespec="seconds"),
            "elapsed_s": round(time.time() - self._started, 2),
            "summary": self.counts(),
            "result": self.overall(),
            "cases": [r.as_dict() for r in self.results],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def finish(self):
        """輸出 Summary 與檔案，回傳 (exit_code, csv_path, json_path)。"""
        c = self.counts()
        line = "=" * 60
        print()
        print(line)
        print(_c("Summary", "bold"))
        print(line)
        print("Total : %s" % c["TOTAL"])
        print("PASS  : %s" % _c(c[PASS], "green"))
        print("FAIL  : %s" % _c(c[FAIL], "red" if c[FAIL] else "grey"))
        print("SKIP  : %s" % _c(c[SKIP], "yellow" if c[SKIP] else "grey"))
        print("Elapsed : %ss" % round(time.time() - self._started, 2))

        if c[FAIL]:
            print()
            print(_c("Failed cases:", "red"))
            for r in self.results:
                if r.status == FAIL:
                    print("  - %s %s :: %s: %s" % (r.case_id, r.name, r.error_type, r.error_msg))

        result = self.overall()
        print()
        print("Result: %s" % _c(result, "green" if result == PASS else "red"))

        csv_path = self.write_csv()
        json_path = self.write_json()
        print("CSV   : %s" % csv_path)
        print("JSON  : %s" % json_path)
        return (0 if result == PASS else 1), csv_path, json_path
