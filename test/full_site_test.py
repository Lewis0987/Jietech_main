# -*- coding: utf-8 -*-
"""全站功能自動化測試 - 入口。

用法：
    python full_site_test.py                # 執行所有已註冊 flow
    python full_site_test.py --list         # 列出可用 flow
    python full_site_test.py --flows header,banner
    python full_site_test.py --smoke        # 只跑框架 smoke test（不需要任何 flow）
    python full_site_test.py --headless
    python full_site_test.py --keep-open    # 結束後不關閉 Chrome

設計原則：
  * 單一 case 失敗 -> 記錄 FAIL + 截圖 + recovery -> 繼續下一個，絕不中斷。
  * 單一 flow 整個爆掉 -> 記錄成該 flow 的 FAIL case -> 繼續下一個 flow。
  * 破壞性操作一律只驗證 found / displayed / enabled，不執行。
"""

import argparse
import importlib
import os
import pkgutil
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config                                    # noqa: E402
from common import download_utils as DL          # noqa: E402
from common import driver_utils as D             # noqa: E402
from common import popup_utils as P              # noqa: E402
from common import recovery as R                 # noqa: E402
from common import wait_utils as W               # noqa: E402
from common.result_utils import Reporter         # noqa: E402

FLOWS_DIR = os.path.join(BASE_DIR, "flows")

# 預設執行順序（未列出的 flow 依字母序排在後面）。
# popup 必須最先跑：popup 只在頁面剛載入時出現，被其他 flow 關掉就測不到了。
FLOW_ORDER = ["popup", "header", "banner", "menu", "safety",
              "mine", "account", "record", "promo", "task", "earn"]


# ====================================================================== Ctx
class Ctx(object):
    """傳給每個 flow 的執行情境。"""

    def __init__(self, driver, reporter, home_url, args):
        self.driver = driver
        self.reporter = reporter
        self.home_url = home_url
        self.args = args
        self.config = config
        self.download_path = config.DOWNLOAD_PATH
        # 讓 flow 直接取用共用工具，不必各自 import
        self.W = W
        self.P = P
        self.DL = DL
        self.D = D
        self.R = R

    # --- 便利方法 -------------------------------------------------
    def log(self, message):
        print("   %s" % message)

    def group(self, letter, title):
        self.reporter.group(letter, title)

    def case(self, case_id, name):
        return self.reporter.case(case_id, name)

    def go_home(self, timeout=20):
        return R.go_home(self.driver, self.home_url, timeout=timeout, log=self.log)

    def close_popups(self):
        return P.close_all(self.driver, log=self.log)

    def is_safe_only(self):
        """True 代表目前只允許「驗證不點擊」的破壞性等級。"""
        return config.SAFE_LEVEL <= 1


# ====================================================================== flow 探索
def discover_flows():
    """掃描 flows/ 目錄，回傳 {name: module_name}。目錄不存在時回傳空 dict。"""
    if not os.path.isdir(FLOWS_DIR):
        return {}
    found = {}
    for mod in pkgutil.iter_modules([FLOWS_DIR]):
        name = mod.name
        if name.startswith("_"):
            continue
        key = name[:-5] if name.endswith("_flow") else name
        found[key] = "flows.%s" % name

    def rank(k):
        return (FLOW_ORDER.index(k), "") if k in FLOW_ORDER else (len(FLOW_ORDER), k)

    return dict((k, found[k]) for k in sorted(found, key=rank))


def load_flow(module_name):
    module = importlib.import_module(module_name)
    if not hasattr(module, "run"):
        raise AttributeError("%s 缺少 run(ctx) 函式" % module_name)
    return module


def run_flow(ctx, key, module_name):
    """執行單一 flow。整個 flow 爆掉也只會變成一筆 FAIL，不中斷後續。"""
    try:
        module = load_flow(module_name)
    except Exception as e:
        ctx.group(key.upper()[:1], "%s (載入失敗)" % key)
        with ctx.case("%s-LOAD" % key.upper()[:1], "load %s" % module_name):
            raise e
        return

    try:
        module.run(ctx)
    except KeyboardInterrupt:
        raise
    except BaseException:                       # noqa: BLE001
        tb = traceback.format_exc(limit=3)
        with ctx.case("%s-CRASH" % key.upper()[:1], "flow %s 中斷" % key) as c:
            c.note(tb.splitlines()[-1] if tb else "")
            raise
    finally:
        # 不論成敗，回到穩定頁面再跑下一個 flow（瀏覽器已死就不要再試）
        if not ctx.reporter.session_dead:
            try:
                ctx.go_home()
            except Exception:
                pass


# ====================================================================== smoke
def run_smoke(ctx):
    """框架 smoke test：驗證 driver / 網站 / popup / 下載路徑 / recovery 都可運作。"""
    driver = ctx.driver
    ctx.group("Z", "Framework Smoke Test")

    with ctx.case("Z-1", "開啟大廳頁面") as c:
        c.action("driver.get(%s)" % ctx.home_url)
        url = D.open_url(driver, ctx.home_url, timeout=config.T_PAGE_LOAD)
        c.check("current_url = %s" % url)
        state = driver.execute_script("return document.readyState")
        if state != "complete":
            raise AssertionError("document.readyState = %s" % state)
        c.check("document.readyState = complete")

    with ctx.case("Z-2", "頁面內容已渲染") as c:
        W.wait_present(driver, W.css("body"), config.T_NORMAL)
        c.found("body 存在")
        count = driver.execute_script(
            "return document.querySelectorAll('img,button,a,input').length")
        if count < 1:
            raise AssertionError("頁面沒有任何可操作元素，可能未載入完成")
        c.check("可操作元素數量 = %s" % count)
        c.note("title = %s" % (driver.title or "(空)"))

    with ctx.case("Z-3", "Popup 偵測與關閉") as c:
        opened = P.detect(driver, timeout=config.T_SHORT)
        c.found("偵測到 popup：%s" % (opened or "無"))
        closed = P.close_all(driver, log=ctx.log)
        c.action("關閉 popup x%s（本站 popup 為連續排隊彈出）" % closed)
        remain = P.detect(driver, timeout=0)
        c.check("殘留 popup：%s" % (remain or "無"))
        c.check("仍有關閉鈕：%s" % P.has_close_button(driver))

    with ctx.case("Z-4", "大廳錨點可辨識") as c:
        hits = [loc[1] for loc in R.HOME_ANCHORS if W.exists(driver, loc, 0)]
        c.found("命中錨點 %s 個" % len(hits))
        for h in hits:
            c.note(h)
        if not hits:
            raise AssertionError(
                "找不到任何大廳錨點；probe 之後需要更新 recovery.HOME_ANCHORS")
        c.check("recovery 可判斷是否位於大廳")

    with ctx.case("Z-5", "下載路徑一致性") as c:
        chrome_path = getattr(driver, "__download_path__", None)
        c.found("config.DOWNLOAD_PATH = %s" % config.DOWNLOAD_PATH)
        c.check("driver 使用路徑     = %s" % chrome_path)
        if chrome_path != config.DOWNLOAD_PATH:
            raise AssertionError("Chrome 與 Python 監控路徑不一致！")
        cdp = getattr(driver, "__download_cdp__", None)
        c.check("CDP 強制下載目錄：%s" % (cdp or "未使用（僅靠 prefs，不會產生垃圾檔）"))
        probe_file = os.path.join(config.DOWNLOAD_PATH, ".jietech_write_test")
        with open(probe_file, "w") as f:
            f.write("ok")
        os.remove(probe_file)
        c.check("下載資料夾可寫入且測試檔已清除")

    with ctx.case("Z-6", "下載前後差集不影響既有檔案") as c:
        before = DL.snapshot(config.DOWNLOAD_PATH)
        c.found("既有檔案 %s 個" % len(before))
        res = DL.wait_for_new_download(config.DOWNLOAD_PATH, before, timeout=2,
                                       extensions=config.DOWNLOAD_EXTENSIONS)
        if res["ok"]:
            raise AssertionError("未點擊下載卻偵測到新檔案：%s" % res["files"])
        c.check("未觸發下載時正確回報 0 個新檔案（不會誤刪既有檔案）")

    with ctx.case("Z-7", "recovery 回到穩定頁面") as c:
        driver.get("about:blank")
        c.action("離開大廳（about:blank）")
        ok = ctx.go_home()
        if not ok:
            raise AssertionError("go_home() 無法回到大廳")
        c.check("已回到大廳：%s" % driver.current_url)

    if ctx.args.inject_failure:
        with ctx.case("Z-9", "故意失敗（驗證截圖/recovery/不中斷）") as c:
            c.found("刻意尋找不存在的元素")
            W.wait_present(driver, W.xp("//div[@id='definitely-not-exist']"), 2)

        with ctx.case("Z-10", "失敗後流程仍繼續") as c:
            c.check("Z-9 失敗後仍執行到此 case")
            if not R.at_home(driver):
                raise AssertionError("recovery 未把頁面帶回大廳")
            c.check("recovery 已把頁面帶回大廳")


# ====================================================================== main
def parse_args(argv=None):
    p = argparse.ArgumentParser(description="全站功能自動化測試")
    p.add_argument("--flows", default="", help="逗號分隔的 flow 名稱；預設全部")
    p.add_argument("--list", action="store_true", help="列出可用 flow 後結束")
    p.add_argument("--smoke", action="store_true", help="只跑框架 smoke test")
    p.add_argument("--env", default=config.UI_VERSION, help="URL.ini section，預設 IN")
    p.add_argument("--product", default=config.PRODUCT, help="URL.ini key，預設 INV6")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--keep-open", action="store_true", help="結束後不關閉 Chrome")
    p.add_argument("--popup-watcher", action="store_true", help="啟用背景 popup 監控")
    p.add_argument("--force-download-cdp", action="store_true",
                   help="用 CDP 強制下載目錄（僅在下載路徑不一致時才需要；"
                        "會在 Downloads 產生 Chrome 元件垃圾檔）")
    p.add_argument("--safe-level", type=int, default=config.SAFE_LEVEL)
    p.add_argument("--inject-failure", action="store_true",
                   help="smoke 時加入一個刻意失敗的 case，驗證錯誤隔離")
    return p.parse_args(argv)


def main(argv=None):
    config.force_utf8_stdout()
    config.ensure_dirs()
    args = parse_args(argv)

    registry = discover_flows()
    if args.list:
        print("可用 flow（預設執行順序）：")
        if registry:
            for k, v in registry.items():
                print("  - %-12s -> %s" % (k, v))
        else:
            print("  (尚未建立任何 flow；請先用 --smoke 驗證框架)")
        return 0

    # 安全守門
    config.SAFE_LEVEL = args.safe_level
    config.assert_safe(args.product, args.safe_level)

    home_url = config.read_url(args.env, args.product)

    selected = [s.strip() for s in args.flows.split(",") if s.strip()] if args.flows else list(registry)
    unknown = [s for s in selected if s not in registry]
    if unknown:
        print("未知的 flow：%s（可用：%s）" % (unknown, sorted(registry) or "無"))
        return 2

    reporter = Reporter(title="IN %s FULL SITE AUTOMATION TEST" % args.product)
    reporter.set_meta(
        Target="%s/%s" % (args.env, args.product),
        URL=home_url,
        Download=DL.describe(config.DOWNLOAD_PATH),
        SafeLevel=config.SAFE_LEVEL,
        Mode="smoke" if args.smoke else ("flows: %s" % (selected or "無")),
    )

    driver = None
    watcher = None
    exit_code = 1
    try:
        driver = D.new_driver(config.DOWNLOAD_PATH, headless=args.headless,
                              page_load_timeout=config.T_PAGE_LOAD,
                              force_cdp=args.force_download_cdp)
        reporter.attach_driver(driver)
        reporter.set_meta(**D.browser_info(driver))
        reporter.header()

        ctx = Ctx(driver, reporter, home_url, args)
        reporter.set_recovery(R.make_recovery(driver, home_url, log=ctx.log))

        if args.popup_watcher or config.POPUP_WATCHER:
            watcher = P.PopupWatcher(driver, log=ctx.log)
            watcher.start()

        if args.smoke or not selected:
            run_smoke(ctx)
            if not selected and not args.smoke:
                print("\n（尚未建立任何 flow，僅執行框架 smoke test）")
        else:
            # 先開站台；刻意不在這裡關 popup，
            # 否則 popup_flow 會因為 popup 已被關掉而全部 SKIP。
            D.open_url(driver, home_url, timeout=config.T_PAGE_LOAD)
            for i, key in enumerate(selected):
                run_flow(ctx, key, registry[key])
                if reporter.session_dead:
                    # 瀏覽器已中斷，後續 flow 全部標記 SKIP 而不是製造一堆假 FAIL
                    print("\n瀏覽器連線已中斷，中止後續 flow。")
                    reporter.group("!", "已中止")
                    for rest in selected[i + 1:]:
                        with reporter.case("%s-ABORT" % rest.upper()[:1],
                                           "flow %s 未執行" % rest) as c:
                            c.skip("瀏覽器連線中斷，未執行")
                    break

    except KeyboardInterrupt:
        print("\n使用者中斷。")
    except BaseException:                        # noqa: BLE001
        print("\n啟動階段發生未預期錯誤：")
        traceback.print_exc(limit=5)
    finally:
        if watcher is not None:
            n = watcher.stop()
            print("背景 popup 監控共關閉 %s 次" % n)
        exit_code = reporter.finish()[0] if reporter.results else 1
        if args.keep_open:
            print("\n--keep-open：Chrome 保持開啟，請自行關閉視窗。")
        else:
            D.quit_driver(driver)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
