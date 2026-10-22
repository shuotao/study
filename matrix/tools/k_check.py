#!/usr/bin/env python3
"""I/IV shared-K gate (SPEC §9). Usage: k_check.py <run_dir>
k-same-set : i.html and iv.html data-k sequence == K.json K1..Kn
k-anchors  : every block's data-anchors non-empty and ⊆ that K's anchors (I's 「讀原文」 links count; cross-run and obsidian: links ignored)
aux/audience: hNNN only allowed in IV; a unit citing only audience paragraphs must say 聽眾
i-length   : i.html content CJK ≤ 1200 (tool-generated how-to/lead excluded)
jargon/supp: per-card ≤1 〔補述：…〕, ≤7 per page; first use of a jargon term (run jargon.txt or tools/jargon_common.txt) must be glossed
iv-breadth : (browser) relations listed == IV data links for this run; ring has spokes when links exist; no JS errors\niv-graph   : (browser, 1280 & 390, depth 1 & 2) visible card-graph labels: 0 crossings with unrelated edges, 0 label overlaps, 0 out of canvas
"""
import sys, re, json
from html.parser import HTMLParser
from pathlib import Path

CJK = re.compile(r"[一-鿿]")
FIELDS = ["claim", "condition", "evidence", "contrast", "boundary"]


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(); self.blocks = []; self.cur = None; self.depth = 0; self.skip = 0; self.text = []
    def handle_starttag(self, tag, a):
        d = dict(a)
        if tag in ("nav", "footer", "script", "style", "svg", "figcaption"): self.skip += 1   # 圖解文字不計入 I 的閱讀字數
        if "data-k" in d and self.cur is None:
            self.cur = {"k": d["data-k"], "anchors": (d.get("data-anchors") or "").split(), "fields": [], "links": [], "tag": tag}
            self.depth = 0
        if self.cur is not None:
            if tag == self.cur["tag"]: self.depth += 1
            if "data-field" in d: self.cur["fields"].append(d["data-field"])
            h = d.get("href", "")
            if tag == "a" and "#p" in h and not h.startswith(("../", "obsidian:")): self.cur["links"].append(h.split("#")[1])
            if d.get("data-anchors") and "data-k" not in d: self.cur["anchors"] += d["data-anchors"].split()
    def handle_endtag(self, tag):
        if tag in ("nav", "footer", "script", "style", "svg", "figcaption"): self.skip -= 1
        if self.cur is not None and tag == self.cur["tag"]:
            self.depth -= 1
            if self.depth == 0: self.blocks.append(self.cur); self.cur = None
    def handle_data(self, data):
        if not self.skip: self.text.append(data)


def parse(f):
    t = f.read_text(encoding="utf-8")
    # 工具產生的讀法說明與導言不算內容字數(§V8.9);只算 LLM 寫的內容
    t = re.sub(r'<section class="n-how.*?</section>|<div class=n-lead>.*?</div>', "", t, flags=re.S)
    p = Blocks(); p.feed(t); return p


def i_jargon_supp(run, K):
    """§V8.4 supp-limits + jargon-gloss(只對 i.html)。"""
    fails = []
    html = (run / "i.html").read_text(encoding="utf-8")
    jf = run / "jargon.txt" if (run / "jargon.txt").exists() else run.parent.parent / "tools/jargon_common.txt"
    terms = [t.strip() for t in jf.read_text().splitlines() if t.strip()]   # 每場可放自己的 jargon.txt
    cards = re.findall(r'<article[^>]*data-k="(K\d+)"[^>]*>(.*?)</article>', html, re.S)
    total = 0
    for k, body in cards:
        supps = re.findall(r'<span class="supp"[^>]*>(.*?)</span>', body, re.S)
        total += len(supps)
        if len(supps) > 1: fails.append(f"supp {k} has {len(supps)} (>1)")
        for sp in supps:
            txt = re.sub(r"<[^>]+>", "", sp)
            if not txt.startswith("〔補述："): fails.append(f"supp {k} not 〔補述：…〕: {txt[:16]}")
            if len(CJK.findall(txt)) > 28 + 2: fails.append(f"supp {k} too long: {txt[:16]}")
            if re.search(r"\d", txt): fails.append(f"supp {k} has digits: {txt[:16]}")
        text = re.sub(r'<a [^>]*href="ii\.html[^>]*>.*?</a>', "", body, flags=re.S)
        plain = re.sub(r"<[^>]+>", "", text)
        title = re.sub(r"<[^>]+>", "", (re.search(r"<h2[^>]*>(.*?)</h2>", body, re.S) or [None, ""])[1])
        for t in terms:
            i = plain.find(t)
            if i < 0: continue
            window = plain[i:i + len(t) + 40]
            terms_glossed = re.findall(r'data-term="([^"]+)"', body) + re.findall(r"〔補述：([^＝〕]+)＝", body)
            glossed = ("（" in window or "〔補述" in window or f'data-term="{t}"' in body
                       or any(g and (g in t or t in g) for g in terms_glossed))   # 「模型」的補述涵蓋「語言模型」
            if not glossed: fails.append(f"jargon {k}: 「{t}」 first use has no gloss")
            if t in title and not ("（" in title or "〔補述" in title):
                fails.append(f"jargon {k}: title has unexplained 「{t}」")
    if total > 7: fails.append(f"supp total {total} > 7")
    # T1 jargon-dropped(WARN):K 的 point 用到的術語,卡片上卻不見了 → 可能為了過 gate 刪掉講者用詞(交人看,不擋)
    exempt = set((run / "jargon_exempt.txt").read_text().split()) if (run / "jargon_exempt.txt").exists() else set()
    kp = {k["k"]: k["point"] for k in K}
    for k, body in cards:
        plain = re.sub(r"<[^>]+>", "", body)
        for t_ in terms:
            if t_ in kp.get(k, "") and t_ not in plain and t_ not in exempt:
                print(f"WARN jargon-dropped {k}: 「{t_}」 in K point but not on card — OK only if replaced by the speaker's plain wording (SPEC W4a rung 3); else gloss it. Silence via jargon_exempt.txt")
    return fails


def main():
    run = Path(sys.argv[1]).resolve(); f = []
    K = json.loads((run / "K.json").read_text(encoding="utf-8"))["K"]
    order = [k["k"] for k in K]; kan = {k["k"]: set(k["anchors"]) for k in K}
    views = {}
    for name in ("i.html", "iv.html"):
        if not (run / name).exists(): f.append(f"{name} missing"); continue
        p = parse(run / name); views[name] = p
        seq = [b["k"] for b in p.blocks]
        if seq != order: f.append(f"{name} data-k {seq} != {order}")
        for b in p.blocks:
            used = set(b["anchors"]) | set(b["links"])
            if not used: f.append(f"{name} {b['k']} no anchors")
            aux_used = {a for a in used if a.startswith("h")}
            if aux_used:   # §V8.7:講者輔助材料錨點只准用在 IV,且必須存在於 aux.anchors.json
                aux = {i["id"] for i in json.loads((run / "aux.anchors.json").read_text(encoding="utf-8"))["items"]} if (run / "aux.anchors.json").exists() else set()
                if name != "iv.html": f.append(f"{name} {b['k']} uses aux anchors {sorted(aux_used)} (IV only)")
                if aux_used - aux: f.append(f"{name} {b['k']} unknown aux anchors {sorted(aux_used - aux)}")
                used = used - aux_used
            out = used - kan.get(b["k"], set())
            if out: f.append(f"{name} {b['k']} anchors outside K: {sorted(out)}")
    spk = json.loads((run / "speakers.json").read_text(encoding="utf-8"))["paragraphs"] if (run / "speakers.json").exists() else {}
    aud_only = {pid for pid, v in spk.items() if v.get("who") == "audience"}
    for name, html_ in (("i.html", run / "i.html"), ("iv.html", run / "iv.html")):
        if not html_.exists() or not aud_only: continue
        t_ = html_.read_text(encoding="utf-8")
        for m in re.finditer(r'<(li|p|article)[^>]*data-anchors="([^"]+)"[^>]*>(.*?)</\1>', t_, re.S):
            ids_ = set(m.group(2).split())
            if ids_ and ids_ <= aud_only and "聽眾" not in re.sub(r"<[^>]+>", "", m.group(3)):
                f.append(f"{name} unit cites only audience paragraphs {sorted(ids_)} but does not say 聽眾")
    if "i.html" in views:
        f += i_jargon_supp(run, K)
        n = len(CJK.findall("".join(views["i.html"].text)))
        if n > 1200: f.append(f"i.html body CJK {n} > 1200")
        print("i.html cjk", n)
    if "iv.html" in views:
        from playwright.sync_api import sync_playwright
        breadth = 'data-view="breadth"' in (run / "iv.html").read_text(encoding="utf-8")
        with sync_playwright() as pw:
            br = pw.chromium.launch(); pg = br.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto((run / "iv.html").as_uri()); pg.wait_for_timeout(300)
            (run / "verify").mkdir(exist_ok=True); pg.screenshot(path=str(run / "verify/iv.png"), full_page=True)
            solo = 'data-solo="1"' in (run / "iv.html").read_text(encoding="utf-8")
            if solo:      # 族譜只有這一場:不得出現場次網/圖譜/關聯
                if pg.evaluate("() => document.querySelectorAll('#ring, #graph, .n-card .rels li').length"): f.append("iv solo page shows sessions/relations")
            elif breadth:   # IV 廣度:每條關聯都要畫成地圖上的一條線,卡片順序 = K
                n_data = pg.evaluate("() => { const h = IV.here, r = id => id.split('#')[0]; return IV.links.filter(l => r(l.a) === h || r(l.b) === h).length }")
                rels = pg.evaluate("() => document.querySelectorAll('.n-card .rels li').length")
                spokes = pg.evaluate("() => [...document.querySelectorAll('#ring .spoke')].length")
                if n_data != rels: f.append(f"iv relations listed {rels} != data {n_data}")
                if n_data and not spokes: f.append("iv ring has no spokes")
                AUDIT = """() => { const svg = document.querySelector('#graph svg'), L = [...svg.querySelectorAll('line')], T = [...svg.querySelectorAll('.gl')].filter(x => getComputedStyle(x).display !== 'none');
                  const W = +svg.getAttribute('width'), H = +svg.getAttribute('height'); let cross = 0, overlap = 0, out = 0;
                  const box = x => { const b = x.getBBox(); return {x: b.x, y: b.y, w: b.width, h: b.height, id: x.dataset.id}; };
                  const X = (ax, ay, bx, by, cx, cy, dx, dy) => { const d = (bx-ax)*(dy-cy)-(by-ay)*(dx-cx); if (!d) return false; const u = ((cx-ax)*(dy-cy)-(cy-ay)*(dx-cx))/d, v = ((cx-ax)*(by-ay)-(cy-ay)*(bx-ax))/d; return u>=0&&u<=1&&v>=0&&v<=1; };
                  const B = T.map(box);
                  B.forEach((r, i) => { if (r.x < 0 || r.y < 0 || r.x + r.w > W || r.y + r.h > H) out++;
                    L.forEach(l => { if (l.dataset.a === r.id || l.dataset.b === r.id) return; const s = [+l.getAttribute('x1'), +l.getAttribute('y1'), +l.getAttribute('x2'), +l.getAttribute('y2')];
                      const ins = (x, y) => x > r.x && x < r.x + r.w && y > r.y && y < r.y + r.h;
                      if (ins(s[0], s[1]) || ins(s[2], s[3]) || [[r.x,r.y,r.x+r.w,r.y],[r.x+r.w,r.y,r.x+r.w,r.y+r.h],[r.x,r.y+r.h,r.x+r.w,r.y+r.h],[r.x,r.y,r.x,r.y+r.h]].some(e => X(...s, ...e))) cross++; });
                    B.slice(i + 1).forEach(q => { if (r.x < q.x + q.w && q.x < r.x + r.w && r.y < q.y + q.h && q.y < r.y + r.h) overlap++; }); });
                  return {labels: T.length, cross, overlap, out}; }"""
                for width in (1280, 390):
                    pg.set_viewport_size({"width": width, "height": 900}); pg.goto((run / "iv.html").as_uri()); pg.wait_for_timeout(300)
                    pg.click('.vt button[data-v="graph"]'); pg.wait_for_timeout(300)
                    for d in ("1", "2"):
                        pg.click(f'.dp button[data-d="{d}"]'); pg.wait_for_timeout(300)
                        a = pg.evaluate(AUDIT)
                        own = pg.evaluate("() => [...document.querySelectorAll('#graph .gn.here')].length - [...document.querySelectorAll('#graph .gn.here .gk')].length")
                        if own: f.append(f"iv-graph @{width} depth {d}: {own} own-session cards unlabelled")
                        if a["cross"] or a["overlap"] or a["out"]:
                            f.append(f"iv-graph @{width} depth {d}: labels={a['labels']} cross={a['cross']} overlap={a['overlap']} out={a['out']} (labels must not touch unrelated edges)")
            if (run / "i.html").exists():
                pg.goto((run / "i.html").as_uri()); pg.screenshot(path=str(run / "verify/i.png"), full_page=True)
            br.close()
        if errs: f.append(f"js errors {errs[:2]}")
    for x in f[:30]: print("FAIL", x)
    print("PASS" if not f else f"{len(f)} failure(s)"); sys.exit(1 if f else 0)



if __name__ == "__main__":
    main()
