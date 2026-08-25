# -*- coding: utf-8 -*-
"""Phase 6-A：/account、/record、/activity 深度唯讀探查。

與 dom_probe 的差異：
    dom_probe   -> 統計 button / img / input / a 等「語意元素」
    deep_probe  -> 額外分析「可互動元素」，因為本站是 React SPA，
                   大量功能是 div + onClick，只看語意標籤會嚴重低估。

【唯讀保證】
    只做：站內導航（點 TabBar / MINE 選單以抵達目標頁）、讀 DOM、輸出 JSON。
    不點擊任何功能按鈕、不輸入、不送出、不 Claim / Redeem / Submit。

用法：
    python -m probe.deep_probe
    python -m probe.deep_probe --headless
"""

import argparse
import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402
from common import dom_scan                      # noqa: E402
from common import driver_utils as D             # noqa: E402
from common import popup_utils as P              # noqa: E402
from common import wait_utils as W               # noqa: E402

MINE_ICON = W.css("img[alt='ic_user']")
PROMO_ICON = W.css("img[alt='ic_activity']")
HOME_ICON = W.css("img[alt='ic_home']")


def _goto_hall(drv, home_url):
    D.open_url(drv, home_url, timeout=config.T_PAGE_LOAD)
    W.settle(2.5)
    P.close_all(drv)
    W.settle(1.0)
    P.close_all(drv)


def _click(drv, locator, wait=1.5):
    W.safe_click(drv, locator, timeout=config.T_NORMAL)
    W.settle(wait)
    W.wait_ready(drv, timeout=config.T_NORMAL)


def goto_account(drv, home_url):
    """大廳 -> MINE -> My info（/account）。"""
    _goto_hall(drv, home_url)
    _click(drv, MINE_ICON)
    _click(drv, W.xp("//button[.//img[@alt='ic_info']]"))
    return drv.current_url


def goto_record(drv, home_url):
    """大廳 -> MINE -> Balance details（/record）。"""
    _goto_hall(drv, home_url)
    _click(drv, MINE_ICON)
    _click(drv, W.xp("//button[.//img[@alt='ic_bank']]"))
    return drv.current_url


def goto_activity(drv, home_url):
    """大廳 -> TabBar PROMO（/activity）。"""
    _goto_hall(drv, home_url)
    _click(drv, PROMO_ICON)
    return drv.current_url


def goto_task_center(drv, home_url):
    """大廳 -> MINE -> Mission（/task_center）。"""
    _goto_hall(drv, home_url)
    _click(drv, MINE_ICON)
    _click(drv, W.xp("//button[.//img[@alt='ic_mission']]"))
    return drv.current_url


TARGETS = [
    ("account", goto_account),
    ("record", goto_record),
    ("activity", goto_activity),
    ("task_center", goto_task_center),
]


def summarize(name, deep, flat):
    """在 terminal 印出重點，完整內容仍寫進 JSON。"""
    print("\n" + "=" * 66)
    print("### %s  ->  %s" % (name.upper(), deep["url"]))
    print("  語意元素: %s" % flat["counts"])
    print("  可互動元素總數: %s（列出前 %s）" % (deep["count"], len(deep["items"])))
    print("  %-4s %-9s %-26s %-8s %-7s %s" % ("y", "tag", "text", "cursor", "react", "img/class"))
    for it in deep["items"]:
        mark = "R" if it["react_onclick"] else ("S" if it["semantic"] else "-")
        extra = it["img_alt"] or (it["cls"].split()[0] if it["cls"] else "")
        print("  %-4s %-9s %-26s %-8s %-7s %s" % (
            it["rect"]["y"], it["tag"], (it["text"] or "")[:26],
            it["cursor"][:8], mark, extra[:44]))


def main(argv=None):
    config.force_utf8_stdout()
    config.ensure_dirs()

    ap = argparse.ArgumentParser(description="Phase 6-A 深度唯讀探查")
    ap.add_argument("--env", default=config.UI_VERSION)
    ap.add_argument("--product", default=config.PRODUCT)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--only", default="", help="只探查指定頁面，逗號分隔")
    args = ap.parse_args(argv)

    home_url = config.read_url(args.env, args.product)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    only = [s.strip() for s in args.only.split(",") if s.strip()]

    result = {"meta": {"run_id": run_id, "url": home_url,
                       "read_only": True,
                       "note": "只做站內導航與 DOM 讀取，未點擊任何功能按鈕"},
              "pages": {}}

    drv = D.new_driver(config.DOWNLOAD_PATH, headless=args.headless,
                       page_load_timeout=config.T_PAGE_LOAD)
    try:
        result["meta"]["browser"] = D.browser_info(drv)
        for name, nav in TARGETS:
            if only and name not in only:
                continue
            try:
                url = nav(drv, home_url)
                deep = dom_scan.scan_interactive(drv, name)
                flat = dom_scan.scan(drv, name, settle=0.3)
                result["pages"][name] = {"url": url, "interactive": deep, "flat": flat}
                summarize(name, deep, flat)
            except Exception as e:
                msg = str(e).split("Stacktrace")[0][:200]
                print("\n### %s 探查失敗：%s" % (name, msg))
                result["pages"][name] = {"error": msg}
    finally:
        D.quit_driver(drv)

    path = os.path.join(str(config.PROBE_DIR), "deep_%s.json" % run_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n輸出：%s" % path)
    return path


if __name__ == "__main__":
    main()
