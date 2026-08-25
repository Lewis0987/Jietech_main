# -*- coding: utf-8 -*-
"""共用的唯讀 DOM 掃描（probe 與 flow 共用同一份 JS）。

probe/dom_probe.py 與 flows/menu_flow.py 都用這裡的 SCAN_JS，
避免兩邊各自維護一份掃描邏輯而失準。

只讀 DOM / attribute，不點擊、不輸入。
"""

import json
import os
import time
from datetime import datetime

SCAN_JS = r"""
const trunc = (s, n) => (s || '').toString().replace(/\s+/g, ' ').trim().slice(0, n);
const rect = e => { const r = e.getBoundingClientRect();
  return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}; };
const vis = e => { const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
const base = e => ({
  tag: e.tagName.toLowerCase(),
  id: e.id || '',
  cls: trunc(e.className, 120),
  text: trunc(e.innerText || e.textContent, 60),
  role: e.getAttribute('role') || '',
  aria: e.getAttribute('aria-label') || '',
  testid: e.getAttribute('data-testid') || e.getAttribute('data-test') || '',
  rect: rect(e), visible: vis(e)
});

// 從 BaseCacheImg class 抽出原始圖片 URL（本站圖片是 blob:，語意藏在 class）
const imgSource = e => {
  const cls = (e.className || '').toString();
  const m = cls.match(/https?:\/\/[^\]\s]+/);
  if (m) return m[0];
  const s = e.currentSrc || e.src || '';
  return s.startsWith('blob:') ? '' : s;
};

const out = {};

out.images = [...document.querySelectorAll('img')].map(e => {
  const src = imgSource(e);
  return Object.assign(base(e), {
    alt: e.alt || '',
    file: src ? src.split('/').pop().split('?')[0] : '',
    src_kind: (e.currentSrc || e.src || '').startsWith('blob:') ? 'blob' : 'url',
    loaded: e.complete && e.naturalWidth > 0
  });
}).filter(o => o.visible || o.alt);

out.buttons = [...document.querySelectorAll('button, [role="button"]')].map(e =>
  Object.assign(base(e), {disabled: !!e.disabled, type: e.getAttribute('type') || ''}));

out.links = [...document.querySelectorAll('a[href]')].map(e =>
  Object.assign(base(e), {
    href: e.href, raw: e.getAttribute('href') || '',
    target: e.getAttribute('target') || '',
    external: (() => { try { return new URL(e.href).host !== location.host; } catch (x) { return false; } })()
  }));

out.inputs = [...document.querySelectorAll('input, textarea')].map(e =>
  Object.assign(base(e), {
    type: (e.type || '').toLowerCase(), name: e.name || '',
    placeholder: e.placeholder || '', checked: !!e.checked,
    disabled: !!e.disabled, readOnly: !!e.readOnly
  }));

out.selects = [...document.querySelectorAll('select')].map(e =>
  Object.assign(base(e), {
    name: e.name || '', disabled: !!e.disabled,
    options: [...e.options].slice(0, 20).map(o => trunc(o.text, 30))
  }));

out.toggles = [...document.querySelectorAll(
  '[role="switch"], [role="checkbox"], [role="radio"], ' +
  '[class*="switch" i], [class*="toggle" i], [class*="checkbox" i], [class*="radio" i]'
)].map(e => Object.assign(base(e), {
  checked: e.getAttribute('aria-checked') || (e.checked === true ? 'true' : ''),
  kind: e.getAttribute('role') || 'class-based'
}));

out.roles = [...document.querySelectorAll('[role]')].map(e =>
  Object.assign(base(e), {role: e.getAttribute('role')}));

out.fixed = [...document.querySelectorAll('*')].filter(e => {
  const cs = getComputedStyle(e);
  if (cs.position !== 'fixed' && cs.position !== 'sticky') return false;
  const r = e.getBoundingClientRect();
  return r.width > 40 && r.height > 20;
}).slice(0, 60).map(e => Object.assign(base(e), {
  position: getComputedStyle(e).position,
  zIndex: getComputedStyle(e).zIndex,
  imgs: [...e.querySelectorAll('img[alt]')].map(i => i.alt).filter(Boolean).slice(0, 15),
  texts: [...e.querySelectorAll('span,div,p')].map(t => trunc(t.innerText, 18))
           .filter(t => t && t.length < 19).slice(0, 15)
}));

// 高 z-index 疊層（popup / modal / toast）；排除瀏覽器注入的極大 z-index 空層
out.overlays = [...document.querySelectorAll('div, section, dialog')].filter(e => {
  const z = parseInt(getComputedStyle(e).zIndex, 10);
  if (!(z >= 100 && z < 1000000)) return false;
  const r = e.getBoundingClientRect();
  if (!(r.width > 100 && r.height > 60)) return false;
  return (e.innerText || '').trim().length > 0 || e.querySelector('img') !== null;
}).slice(0, 30).map(e => Object.assign(base(e), {
  zIndex: getComputedStyle(e).zIndex,
  imgs: [...e.querySelectorAll('img[alt]')].map(i => i.alt).filter(Boolean).slice(0, 10),
  buttons: [...e.querySelectorAll('button')].map(b => trunc(b.innerText, 24)).filter(Boolean).slice(0, 10)
}));

out.swipers = [...document.querySelectorAll('div.swiper')].slice(0, 8).map(sw => ({
  cls: trunc(sw.className, 100),
  rect: rect(sw),
  direction: sw.className.includes('swiper-vertical') ? 'vertical' : 'horizontal',
  slides: sw.querySelectorAll('.swiper-slide').length,
  items: [...sw.querySelectorAll('.swiper-slide')].slice(0, 15).map((s, i) => {
    const img = s.querySelector('img');
    const src = img ? imgSource(img) : '';
    return {
      i: i,
      slide_index: s.getAttribute('data-swiper-slide-index'),
      alt: img ? (img.alt || '') : null,
      file: src ? src.split('/').pop().split('?')[0] : '',
      url: trunc(src, 160),
      text: trunc(s.innerText, 60),
      loaded: img ? (img.complete && img.naturalWidth > 0) : null,
      slide_cls: trunc(s.className, 80)
    };
  })
}));

out.iframes = [...document.querySelectorAll('iframe')].map(e => ({
  id: e.id || '', cls: trunc(e.className, 60),
  src: trunc(e.src || '', 120), rect: rect(e)
}));

out.texts = [...document.querySelectorAll('h1,h2,h3,span,div,p')]
  .map(e => trunc(e.innerText, 40))
  .filter(t => t && t.length > 1 && t.length < 41)
  .filter((t, i, a) => a.indexOf(t) === i).slice(0, 60);

out.counts = {
  img: document.querySelectorAll('img').length,
  button: document.querySelectorAll('button').length,
  a_href: document.querySelectorAll('a[href]').length,
  input: document.querySelectorAll('input').length,
  select: document.querySelectorAll('select').length,
  checkbox: document.querySelectorAll('input[type=checkbox]').length,
  radio: document.querySelectorAll('input[type=radio]').length,
  role: document.querySelectorAll('[role]').length,
  iframe: document.querySelectorAll('iframe').length
};
out.page = {url: location.href, title: document.title,
            viewport: [window.innerWidth, window.innerHeight],
            scrollHeight: document.body.scrollHeight};
return out;
"""


# ------------------------------------------------------------------ 可互動元素
# 本站是 React SPA，大量功能是 div + onClick，光統計 button/input/a 會嚴重低估。
# 這段用多重訊號判斷「使用者實際可以點的東西」：
#   1. 語意標籤（button / a / input / select）
#   2. role / tabindex
#   3. computed cursor: pointer
#   4. inline onclick
#   5. React fiber 上掛著 onClick handler（__reactProps$ / __reactEventHandlers$）
INTERACTIVE_JS = r"""
const trunc = (s, n) => (s || '').toString().replace(/\s+/g, ' ').trim().slice(0, n);

function reactClick(el) {
  for (const k in el) {
    if (k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$')) {
      const p = el[k];
      if (p && (typeof p.onClick === 'function' || typeof p.onPointerDown === 'function')) return true;
    }
  }
  return false;
}

function dataAttrs(el) {
  const out = {};
  for (const a of el.attributes) {
    if (a.name.startsWith('data-')) out[a.name] = trunc(a.value, 60);
  }
  return out;
}

function pathOf(el) {
  const parts = [];
  let n = el;
  for (let i = 0; i < 4 && n && n.tagName; i++) {
    const c = (n.className || '').toString().split(/\s+/).filter(Boolean)[0] || '';
    parts.unshift(n.tagName.toLowerCase() + (c ? '.' + c : ''));
    n = n.parentElement;
  }
  return parts.join(' > ');
}

const out = [];
document.querySelectorAll('body *').forEach(el => {
  const tag = el.tagName.toLowerCase();
  if (tag === 'script' || tag === 'style' || tag === 'svg' || tag === 'path') return;

  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  const semantic = ['button', 'a', 'input', 'select', 'textarea'].includes(tag);
  const role = el.getAttribute('role') || '';
  const tabindex = el.getAttribute('tabindex');
  const pointer = cs.cursor === 'pointer';
  const inlineClick = !!el.getAttribute('onclick');
  const rClick = reactClick(el);

  if (!(semantic || role || tabindex !== null || pointer || inlineClick || rClick)) return;
  if (r.width <= 0 || r.height <= 0) return;
  if (r.width > 1200 && r.height > 600) return;   // 整頁遮罩之類的容器略過

  // 父層已被判定可互動且文字相同 -> 只留最內層，避免整串巢狀重複。
  // 但父層若本身高度為 0（版面塌陷），子層才是使用者真正看得到的部分，不可略過。
  const parent = el.parentElement;
  if (parent && !semantic) {
    const pr = parent.getBoundingClientRect();
    if (pr.height > 0 && getComputedStyle(parent).cursor === 'pointer'
        && trunc(parent.innerText, 40) === trunc(el.innerText, 40)) return;
  }

  // 被其他元素完全遮住 -> 使用者實際點不到，標記出來
  let obscured = null;
  try {
    const top = document.elementFromPoint(
      Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2));
    obscured = !(top === el || el.contains(top) || (top && top.contains(el)));
  } catch (e) {}

  const img = el.querySelector('img');
  out.push({
    tag: tag,
    text: trunc(el.innerText || el.value || '', 50),
    cls: trunc(el.className, 110),
    id: el.id || '',
    role: role,
    tabindex: tabindex,
    cursor: cs.cursor,
    inline_onclick: inlineClick,
    react_onclick: rClick,
    semantic: semantic,
    disabled: !!el.disabled,
    type: el.getAttribute('type') || '',
    placeholder: el.getAttribute('placeholder') || '',
    img_alt: img ? (img.alt || '') : '',
    imgs: [...el.querySelectorAll('img')].map(i => i.alt || '').filter(Boolean).slice(0, 6),
    data: dataAttrs(el),
    rect: {x: Math.round(r.x), y: Math.round(r.y),
           w: Math.round(r.width), h: Math.round(r.height)},
    displayed: cs.visibility !== 'hidden' && cs.display !== 'none',
    obscured: obscured,
    path: pathOf(el),
    children: el.children.length
  });
});

out.sort((a, b) => a.rect.y - b.rect.y || a.rect.x - b.rect.x);
return {url: location.href, title: document.title,
        viewport: [window.innerWidth, window.innerHeight],
        count: out.length, items: out.slice(0, 120)};
"""


def scan_interactive(driver, label, settle=1.0):
    """回傳頁面上所有「使用者實際可點」的元素（唯讀）。"""
    if settle:
        time.sleep(settle)
    data = driver.execute_script(INTERACTIVE_JS)
    data["label"] = label
    data["scanned_at"] = datetime.now().isoformat(timespec="seconds")
    return data


def scan(driver, label, settle=1.2):
    """對目前頁面做一次唯讀掃描。"""
    if settle:
        time.sleep(settle)
    data = driver.execute_script(SCAN_JS)
    data["label"] = label
    data["scanned_at"] = datetime.now().isoformat(timespec="seconds")
    return data


def save(data, out_dir, name):
    """把掃描結果寫成 JSON，回傳路徑。"""
    os.makedirs(str(out_dir), exist_ok=True)
    path = os.path.join(str(out_dir), "snapshot_%s_%s.json"
                        % (name, datetime.now().strftime("%Y%m%d_%H%M%S")))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def summarize(data):
    """給 case log 用的一行摘要。"""
    c = data.get("counts", {})
    return ("img=%s button=%s input=%s select=%s checkbox=%s radio=%s iframe=%s overlay=%s"
            % (c.get("img"), c.get("button"), c.get("input"), c.get("select"),
               c.get("checkbox"), c.get("radio"), c.get("iframe"),
               len(data.get("overlays", []))))
