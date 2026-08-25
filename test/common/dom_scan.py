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
