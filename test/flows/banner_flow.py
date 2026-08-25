# -*- coding: utf-8 -*-
"""[C] 首頁 Banner 廣告模塊。

Phase 4 改版依據（Phase 3 DOM Probe 實測）：
  * 舊的 11 個 alt（0_DYNAMIC_ACTIVITY / 1_ENTER_GAME ...）在本站已完全不存在，
    所有 banner img 的 alt 一律是 'Fallback'，圖片是 blob: URL。
  * 圖片檔名 9/10 是後台上傳的 MD5（/upload/admin/announcement/xxx.webp），
    後台一換就失效 -> 不可作為 selector。
  * slide 具有 Swiper 維護的穩定屬性 data-swiper-slide-index="N"。

因此定位改為：
    div.swiper.swiper-horizontal div[data-swiper-slide-index='N']

語意（哪一格是哪個活動）不寫死，改成執行期記錄
（slide index / img class / 圖片來源 / 是否可點）。

lazy-load / loop 處理：
  Swiper 為 loop + autoplay，同一時間只渲染 active 及鄰近 slide。
  流程：停用 autoplay -> slideToLoop(i) -> 只操作 .swiper-slide-active，
  絕不直接點 hidden / duplicated slide。

破壞性保護：Collect / SPIN / Deposit 一律只驗證，不點擊。
"""

from selenium.webdriver.common.by import By

SWIPER = (By.CSS_SELECTOR, "div.swiper.swiper-horizontal")
ACTIVE_SLIDE = (By.CSS_SELECTOR,
                "div.swiper.swiper-horizontal div.swiper-slide-active")
# 供報告 / 除錯使用的位置定位樣板
SLIDE_TEMPLATE = "div.swiper.swiper-horizontal div[data-swiper-slide-index='%d']"

TAKEN_DOWN = (By.XPATH, '//div[contains(text(), "This game has been taken down")]')
BACK_ICON = (By.XPATH, "//img[contains(@alt,'ic_back_header')]")

# 進入子頁面 / modal 的判斷錨點
ENTERED_ANCHORS = [
    BACK_ICON,
    (By.CSS_SELECTOR, "div[class*='z-[1005]']"),
    (By.CSS_SELECTOR, "img[alt='ic_close']"),
]

# 只驗證、不點擊
DESTRUCTIVE = [
    ("Collect", (By.XPATH, "//button[contains(., 'Collect')]")),
    ("SPIN", (By.XPATH, "//span[contains(text(), 'SPIN')]")),
    ("Deposit", (By.XPATH, "//button[contains(., 'Deposit')]")),
]

MAX_BANNERS = 15          # 安全上限，避免異常時無限迴圈


# ------------------------------------------------------------------ Swiper JS
INIT_JS = """
const el = document.querySelector('div.swiper.swiper-horizontal');
if (!el || !el.swiper) return null;
const sw = el.swiper;
// 停用自動輪播，讓每個 case 的 active slide 是確定的（僅前端行為，重新整理即復原）
try { if (sw.autoplay && sw.autoplay.stop) sw.autoplay.stop(); } catch (e) {}
const idx = new Set([...el.querySelectorAll('[data-swiper-slide-index]')]
              .map(s => s.getAttribute('data-swiper-slide-index')));
const h = e => Math.round(e.getBoundingClientRect().height);
const allSlides = [...el.querySelectorAll('.swiper-slide')];
// 只看「真的有圖片」的 slide：沒有圖片的空 slide 高度會是版面殘留值，不能當基準
const imgSlides = allSlides.filter(s => s.querySelector('img'));
const imgHeights = imgSlides.map(s => h(s.querySelector('img')));
return {total: idx.size, dom_slides: allSlides.length,
        loop: !!sw.params.loop, realIndex: sw.realIndex,
        swiper_h: h(el), wrapper_h: h(el.querySelector('.swiper-wrapper')),
        max_slide_h: allSlides.length ? Math.max.apply(null, allSlides.map(h)) : 0,
        img_slides: imgSlides.length,
        max_img_h: imgHeights.length ? Math.max.apply(null, imgHeights) : -1,
        swiper_cls: (el.className || '').toString()};
"""

GOTO_JS = """
const el = document.querySelector('div.swiper.swiper-horizontal');
if (!el || !el.swiper) return false;
const sw = el.swiper;
try { if (sw.autoplay && sw.autoplay.stop) sw.autoplay.stop(); } catch (e) {}
if (typeof sw.slideToLoop === 'function') { sw.slideToLoop(arguments[0], 0); }
else { sw.slideTo(arguments[0], 0); }
return true;
"""

ACTIVE_JS = """
const el = document.querySelector('div.swiper.swiper-horizontal');
if (!el) return null;
const s = el.querySelector('.swiper-slide-active');
if (!s) return null;
const img = s.querySelector('img');
const cls = img ? (img.className || '').toString() : '';
const m = cls.match(/https?:\\/\\/[^\\]\\s]+/);
const url = m ? m[0] : '';
const r = s.getBoundingClientRect();
return {
  slide_index: s.getAttribute('data-swiper-slide-index'),
  has_img: !!img,
  alt: img ? (img.alt || '') : '',
  img_cls: cls.slice(0, 110),
  src_kind: img ? ((img.currentSrc || img.src || '').startsWith('blob:') ? 'blob' : 'url') : '',
  source_url: url,
  file: url ? url.split('/').pop().split('?')[0] : '',
  loaded: img ? (img.complete && img.naturalWidth > 0) : false,
  visible: r.width > 0 && r.height > 0,
  rect: {w: Math.round(r.width), h: Math.round(r.height)}
};
"""


def _active_info(driver):
    try:
        return driver.execute_script(ACTIVE_JS)
    except Exception:
        return None


def _goto(driver, index):
    try:
        return bool(driver.execute_script(GOTO_JS, index))
    except Exception:
        return False


def run(ctx):
    W, P = ctx.W, ctx.P
    driver = ctx.driver
    cfg = ctx.config

    ctx.group("C", "首頁 Banner")

    if not ctx.R.at_home(driver):
        ctx.go_home()
    P.close_all(driver, log=ctx.log)
    W.settle(1.5)

    total = 0
    records = []

    collapsed = False

    # ============================================================== C-00
    with ctx.case("C-00", "Banner 輪播容器盤點與可視性") as c:
        if not W.exists(driver, SWIPER, cfg.T_NORMAL):
            c.skip("找不到 banner 輪播容器")
        c.found("找到輪播容器 div.swiper.swiper-horizontal")

        info = driver.execute_script(INIT_JS)
        if not info:
            raise AssertionError("Swiper 實例不可用，無法安全遍歷 slide")
        total = min(int(info["total"]), MAX_BANNERS)
        c.check("distinct data-swiper-slide-index = %s（DOM slide %s，loop=%s）"
                % (info["total"], info["dom_slides"], info["loop"]))
        c.action("已停用 autoplay，改為逐格 slideToLoop 控制")
        if total <= 0:
            c.skip("輪播內沒有任何 slide")

        # 可視性：以「有圖片的 slide」為基準；圖片高度 0 代表使用者看不到也點不到
        c.check("尺寸量測 swiper=%spx wrapper=%spx max_slide=%spx；"
                "有圖 slide %s 個，圖片最大高度=%spx"
                % (info["swiper_h"], info["wrapper_h"], info["max_slide_h"],
                   info["img_slides"], info["max_img_h"]))
        if int(info["img_slides"]) > 0 and int(info["max_img_h"]) <= 0:
            collapsed = True
            suspect = "min-h-max]" if "min-h-max]" in info.get("swiper_cls", "") else ""
            raise AssertionError(
                "【已確認現象】Banner DOM 與圖片存在（%s 格 slide、%s 個含圖），"
                "圖片已載入完成，但渲染高度為 0（輪播容器僅 %spx），"
                "使用者畫面實際看不到、也無法點擊。"
                "【疑似原因】swiper class 中出現 %r，疑似 Tailwind class 拼寫異常"
                "導致高度規則未生效——尚未經修改前後驗證，僅為推測。"
                % (info["dom_slides"], info["img_slides"], info["swiper_h"],
                   suspect or info.get("swiper_cls", "")[:60]))

    if total <= 0:
        with ctx.case("C-99", "Banner 流程收尾") as c:
            c.skip("沒有可測試的 Banner")
        return

    # ============================================================== C-01 ~ C-NN
    for i in range(total):
        case_id = "C-%02d" % (i + 1)
        selector = SLIDE_TEMPLATE % i

        with ctx.case(case_id, "Banner slide #%d" % i) as c:
            # 每個 banner 都從乾淨的大廳出發
            if not ctx.R.at_home(driver):
                ctx.go_home()
            P.close_all(driver)

            if not W.exists(driver, SWIPER, cfg.T_SHORT):
                c.skip("輪播容器已不存在")
            if not _goto(driver, i):
                c.skip("Swiper API 不可用，無法定位到 slide #%d" % i)
            W.settle(0.9)

            info = _active_info(driver)
            if not info:
                c.skip("讀不到 active slide")
            if str(info.get("slide_index")) != str(i):
                c.skip("slideToLoop 後 active 仍停在 #%s（lazy/virtual slide）"
                       % info.get("slide_index"))
            # 先記錄語意資訊（不作為 selector），即使之後 SKIP 也留下紀錄
            c.found("locator=%s" % selector)
            c.check("圖片來源=%s（alt=%r, src=%s, loaded=%s, %sx%s）"
                    % (info["file"] or "(無)", info["alt"], info["src_kind"],
                       info["loaded"], info["rect"]["w"], info["rect"]["h"]))
            records.append({"slide": i, "file": info["file"], "url": info["source_url"]})

            if not info.get("has_img"):
                c.skip("slide #%d 尚未渲染圖片（lazy-load）" % i)
            if not info.get("visible"):
                c.skip("slide #%d 尺寸為 %sx%s，畫面上不可見（見 C-00 的塌陷問題）"
                       % (i, info["rect"]["w"], info["rect"]["h"]))

            # Action：只點目前可見的 active slide，不碰 hidden / duplicated slide
            probe_info = W.probe(driver, ACTIVE_SLIDE, timeout=cfg.T_SHORT)
            if not probe_info["clickable"]:
                c.skip("active slide 不可點擊（displayed=%s enabled=%s）"
                       % (probe_info["displayed"], probe_info["enabled"]))

            before_url = driver.current_url
            W.safe_click(driver, ACTIVE_SLIDE, timeout=cfg.T_NORMAL)
            c.action("已點擊 active slide #%d" % i)
            W.settle(1.2)

            # 活動下架 -> SKIP
            if W.exists(driver, TAKEN_DOWN, cfg.T_SHORT):
                c.note("偵測到 This game has been taken down")
                ctx.go_home()
                c.skip("活動 / 遊戲已下架")

            # Post-condition
            entered = None
            for loc in ENTERED_ANCHORS:
                if W.exists(driver, loc, cfg.T_SHORT):
                    entered = loc[1]
                    break
            if entered:
                c.check("已進入子頁面 / modal，錨點：%s" % entered)
                minfo = P.modal_info(driver)
                if minfo:
                    c.note("modal 內容：imgs=%s buttons=%s"
                           % (minfo.get("imgs")[:5], minfo.get("buttons")[:5]))
            elif driver.current_url != before_url:
                c.check("URL 已變更：%s" % driver.current_url)
            else:
                raise AssertionError("點擊 slide #%d 後畫面無變化" % i)

            # 破壞性元素：只驗證，不點擊
            for label, loc in DESTRUCTIVE:
                p = W.probe(driver, loc, timeout=1)
                if p["found"]:
                    c.check("[只驗證不點擊] %s displayed=%s enabled=%s clickable=%s"
                            % (label, p["displayed"], p["enabled"], p["clickable"]))

            # Recovery
            if not ctx.go_home():
                raise AssertionError("無法從 slide #%d 返回大廳" % i)
            c.check("已返回大廳：%s" % driver.current_url)

    # ============================================================== C-99
    with ctx.case("C-99", "Banner 流程收尾") as c:
        c.check("輪播共 %d 格，已產生 %d 個 case" % (total, total))
        if collapsed:
            c.note("本次所有 slide 因容器塌陷而 SKIP，詳見 C-00")
        c.check("本次取得圖片來源 %d 筆" % len(records))
        for r in records:
            c.note("slide #%s -> %s" % (r["slide"], r["file"] or "(無圖)"))
        if not ctx.R.at_home(driver):
            ctx.go_home()
        if not ctx.R.at_home(driver):
            raise AssertionError("Banner 流程結束後未停留在大廳")
        c.check("停留於大廳：%s" % driver.current_url)
