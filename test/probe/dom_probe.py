# -*- coding: utf-8 -*-
"""唯讀 DOM 探測器 —— 盤點網站實際存在的可操作元素。

【唯讀保證】
    允許：driver.get() / 讀 DOM / 讀 attribute / 讀 href /
          判斷 displayed / enabled / 輸出 JSON
    禁止：點擊任何功能按鈕、輸入、送出、Deposit / Withdraw /
          Collect / SPIN / Submit / Redeem / Delete ...

    預設模式完全不點擊任何元素（--popup-queue 例外，見下）。

【--popup-queue（預設關閉）】
    本站 popup 是排隊彈出：不關掉第一個就看不到第二個。
    開啟後【只會】點擊 popup 的關閉鈕（ic_close / Later），
    並在關閉前先把該 popup 的 DOM 快照下來。
    不會點任何功能按鈕。輸出中會標記 source="popup-queue"。

用法：
    python -m probe.dom_probe                  # 嚴格唯讀，只掃大廳
    python -m probe.dom_probe --routes         # 追加掃描 DOM 內找到的同站路由
    python -m probe.dom_probe --popup-queue    # 追加 popup 佇列快照
    python -m probe.dom_probe --headless
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402
from common import dom_scan                      # noqa: E402
from common import driver_utils as D             # noqa: E402
from common import popup_utils as P              # noqa: E402
from common import wait_utils as W               # noqa: E402

MAX_ROUTES = 12

# ====================================================================== JS
# 掃描 JS 已抽到 common/dom_scan.py，probe 與 flow 共用同一份
SCAN_JS = dom_scan.SCAN_JS

# 抓單一 popup 內部細節（--popup-queue 用；快照後才關閉）
POPUP_JS = r"""
const trunc = (s, n) => (s || '').toString().replace(/\s+/g, ' ').trim().slice(0, n);
// 排除瀏覽器 / 擴充套件注入的極大 z-index 空層（z 約 2^31），
// 並要求該層真的有內容（文字或圖片），否則抓到的會是空 div。
const cands = [...document.querySelectorAll('div, section, dialog')].filter(e => {
  const z = parseInt(getComputedStyle(e).zIndex, 10);
  if (!(z >= 100 && z < 1000000)) return false;
  const r = e.getBoundingClientRect();
  if (!(r.width > 150 && r.height > 100)) return false;
  return (e.innerText || '').trim().length > 0 || e.querySelector('img') !== null;
});
if (!cands.length) return null;
cands.sort((a, b) => parseInt(getComputedStyle(b).zIndex,10) - parseInt(getComputedStyle(a).zIndex,10));
const e = cands[0];
return {
  tag: e.tagName.toLowerCase(), id: e.id || '', cls: trunc(e.className, 200),
  zIndex: getComputedStyle(e).zIndex, role: e.getAttribute('role') || '',
  testid: e.getAttribute('data-testid') || '',
  text: trunc(e.innerText, 200),
  imgs: [...e.querySelectorAll('img')].map(i => ({alt: i.alt || '',
        cls: trunc(i.className, 90)})).slice(0, 12),
  buttons: [...e.querySelectorAll('button')].map(b => trunc(b.innerText, 30)).slice(0, 10),
  child_cls: [...e.children].map(ch => trunc(ch.className, 80)).slice(0, 8)
};
"""


# ====================================================================== 掃描
def scan(driver, label, settle=2.0):
    """對目前頁面做一次唯讀掃描。"""
    W.wait_ready(driver, timeout=config.T_NORMAL)
    time.sleep(settle)          # 等前端渲染完成（不點擊任何東西）
    data = driver.execute_script(SCAN_JS)
    data["label"] = label
    data["scanned_at"] = datetime.now().isoformat(timespec="seconds")
    return data


def scan_scrolled(driver, label):
    """捲到底再掃一次，抓出 lazy-load 之後才出現的元素（捲動不改變網站狀態）。"""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        data = scan(driver, label, settle=1.0)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.8)
        return data
    except Exception:
        return None


BANNER_SAMPLE_JS = r"""
const sw = document.querySelector('div.swiper.swiper-horizontal');
if (!sw) return null;
const imgSource = e => {
  const cls = (e.className || '').toString();
  const m = cls.match(/https?:\/\/[^\]\s]+/);
  return m ? m[0] : (e.currentSrc || e.src || '');
};
return [...sw.querySelectorAll('.swiper-slide')].map((s, i) => {
  const img = s.querySelector('img');
  if (!img) return null;
  const src = imgSource(img);
  return {slide: i, alt: img.alt || '',
          file: src ? src.split('/').pop().split('?')[0] : '',
          url: src,
          active: s.className.includes('swiper-slide-active')};
}).filter(Boolean);
"""


def watch_banner(driver, seconds=45, interval=1.5):
    """唯讀觀察 banner 輪播一輪，收集所有 slide 的圖片來源。

    banner 是 lazy-load：同一時間只渲染 active 及其前後的 slide，
    因此必須讓它自己輪播，逐次取樣才能拿到完整清單。全程不點擊。
    """
    seen = {}
    samples = 0
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            rows = driver.execute_script(BANNER_SAMPLE_JS) or []
        except Exception:
            break
        samples += 1
        for r in rows:
            if not r.get("file"):
                continue
            key = r["file"]
            if key not in seen:
                seen[key] = {"file": key, "url": r["url"], "alt": r["alt"],
                             "first_seen_slide": r["slide"]}
        time.sleep(interval)
    return {"samples": samples, "duration_s": seconds,
            "distinct": sorted(seen.values(), key=lambda x: x["first_seen_slide"]),
            "distinct_count": len(seen)}


def probe_popup_queue(driver, home_url, max_rounds=10):
    """【會點擊 popup 關閉鈕】逐一快照排隊彈出的 popup。"""
    snapshots = []
    D.open_url(driver, home_url, timeout=config.T_PAGE_LOAD)
    time.sleep(2.0)

    for _ in range(max_rounds):
        detected = P.detect(driver, timeout=2.0)
        try:
            detail = driver.execute_script(POPUP_JS)
        except Exception:
            detail = None
        if not detected and not detail:
            break
        snapshots.append({
            "known_keys": detected,
            "top_overlay": detail,
            "source": "popup-queue",
        })
        if not P.close_once(driver):
            break
        time.sleep(1.5)
    return snapshots


def collect_routes(page, home_url):
    """從掃描結果取出同站路由（僅讀 href，不點擊）。"""
    try:
        from urllib.parse import urlparse
    except ImportError:
        return []
    host = urlparse(home_url).netloc
    seen, routes = set(), []
    for link in page.get("links", []):
        href = link.get("href", "")
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        u = urlparse(href)
        if u.netloc and u.netloc != host:
            continue
        path = u.path or "/"
        if path in seen:
            continue
        seen.add(path)
        routes.append({"path": path, "url": href, "text": link.get("text", "")})
    return routes[:MAX_ROUTES]


# ====================================================================== main
def main(argv=None):
    config.force_utf8_stdout()
    config.ensure_dirs()

    ap = argparse.ArgumentParser(description="唯讀 DOM 探測")
    ap.add_argument("--env", default=config.UI_VERSION)
    ap.add_argument("--product", default=config.PRODUCT)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--routes", action="store_true", help="追加掃描 DOM 內找到的同站路由")
    ap.add_argument("--banner-watch", type=int, default=0, metavar="SEC",
                    help="唯讀觀察 banner 輪播 N 秒，收集所有 slide 圖片來源")
    ap.add_argument("--popup-queue", action="store_true",
                    help="追加 popup 佇列快照（會點擊 popup 關閉鈕，不點功能按鈕）")
    args = ap.parse_args(argv)

    home_url = config.read_url(args.env, args.product)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "meta": {
            "run_id": run_id,
            "target": "%s/%s" % (args.env, args.product),
            "url": home_url,
            "headless": args.headless,
            "read_only": not args.popup_queue,
            "note": "預設完全不點擊；--popup-queue 只會點 popup 關閉鈕",
        },
        "pages": [],
        "banner_watch": None,
        "popup_queue": [],
    }

    driver = D.new_driver(config.DOWNLOAD_PATH, headless=args.headless,
                          page_load_timeout=config.T_PAGE_LOAD)
    try:
        result["meta"]["browser"] = D.browser_info(driver)

        print("掃描大廳（不點擊任何元素）...")
        D.open_url(driver, home_url, timeout=config.T_PAGE_LOAD)
        hall = scan(driver, "hall")
        result["pages"].append(hall)
        print("  元素統計：%s" % hall["counts"])

        scrolled = scan_scrolled(driver, "hall-scrolled")
        if scrolled:
            result["pages"].append(scrolled)
            print("  捲動後：%s" % scrolled["counts"])

        if args.banner_watch:
            print("觀察 banner 輪播 %ds（不點擊）..." % args.banner_watch)
            result["banner_watch"] = watch_banner(driver, args.banner_watch)
            print("  取得 %d 個不重複 banner 圖片"
                  % result["banner_watch"]["distinct_count"])

        if args.routes:
            routes = collect_routes(hall, home_url)
            print("發現同站路由 %d 個" % len(routes))
            for r in routes:
                if r["path"] in ("/hall", "/"):
                    continue
                print("  掃描 %s ..." % r["path"])
                try:
                    D.open_url(driver, r["url"], timeout=config.T_PAGE_LOAD)
                    result["pages"].append(scan(driver, "route:%s" % r["path"]))
                except Exception as e:
                    result["pages"].append({"label": "route:%s" % r["path"],
                                            "error": str(e).split("Stacktrace")[0]})

        if args.popup_queue:
            print("Popup 佇列快照（只點關閉鈕）...")
            result["popup_queue"] = probe_popup_queue(driver, home_url)
            print("  取得 %d 個 popup 快照" % len(result["popup_queue"]))

    finally:
        D.quit_driver(driver)

    out_path = os.path.join(str(config.PROBE_DIR), "probe_%s.json" % run_id)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n輸出：%s" % out_path)
    return out_path


if __name__ == "__main__":
    main()
