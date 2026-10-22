#!/usr/bin/env python3
"""四頁版面閘門(Playwright 實際渲染,不看原始碼)。用法: ui_check.py <run_dir>
U1 字級下限:畫面上可見文字(含 SVG 圖解,依實際縮放換算)≥ 14px
U2 讀法說明:i/ii/iii/iv 都有「這頁怎麼讀」(.n-how,三步)
U3 共用元件:i/ii/iii/iv 都由共用外殼產生(.n-page + .n-mast);舊版手寫頁會在這裡紅燈
U4 不溢出:桌機 1280 與手機 390 寬度下,頁面沒有水平捲動
"""
import sys
from pathlib import Path

MIN = 14
PAGES = ["index.html", "i.html", "ii.html", "iii.html", "iv.html"]
JS = """(min) => {
  const bad = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; let lo = 99;
  while ((n = w.nextNode())) {
    const t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el || el.closest('script,style,title,desc')) continue;
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (!r.width || !r.height || cs.visibility === 'hidden' || cs.display === 'none' || el.closest('[hidden],details:not([open]) > :not(summary)')) continue;
    let fs = parseFloat(cs.fontSize);
    if (el instanceof SVGElement && el.ownerSVGElement) {        // SVG:字級 × 實際縮放
      const m = el.ownerSVGElement.getScreenCTM(); if (m) fs = fs * m.a;
    }
    lo = Math.min(lo, fs);
    if (fs < min - 0.05) bad.push(`${fs.toFixed(1)}px「${t.slice(0, 14)}」<${el.tagName.toLowerCase()} class=${el.className.baseVal ?? el.className}>`);
  }
  return {lo, bad: [...new Set(bad)]};
}"""


def main():
    run = Path(sys.argv[1]).resolve(); f = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for width in (1280, 390):
            pg = b.new_page(viewport={"width": width, "height": 900})
            for name in PAGES:
                if not (run / name).exists(): continue
                pg.goto((run / name).as_uri()); pg.wait_for_timeout(150)
                r = pg.evaluate(JS, MIN)                                     # U1 兩種寬度都量(手機上 SVG 會縮小)
                print(f"{name:10} @{width} min font {r['lo']:.1f}px")
                for x in r["bad"][:6]: f.append(f"U1 {name} @{width} {x}")
                if len(r["bad"]) > 6: f.append(f"U1 {name} @{width} … 另有 {len(r['bad']) - 6} 處")
                if width == 1280:
                    if name != "index.html":
                        steps = pg.evaluate("() => document.querySelectorAll('.n-how li').length")
                        if steps != 3: f.append(f"U2 {name} 沒有「這頁怎麼讀」三步(找到 {steps})")
                        if not pg.evaluate("() => !!document.querySelector('.n-page .n-mast')"): f.append(f"U3 {name} 不是共用外殼產生(舊版手寫頁)")
                over = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
                if over > 1: f.append(f"U4 {name} 寬 {width} 水平溢出 {over}px")
            pg.close()
        b.close()
    for x in f: print("FAIL", x)
    print("ui", "PASS" if not f else f"FAIL {len(f)}")
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
