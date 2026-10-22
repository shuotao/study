#!/usr/bin/env python3
"""象限 I 圖解驗收。用法: diagram_check.py <run_dir>
D1 每圖 ≤9 節點、≤12 箭頭、型別合法  D2 每節點/箭頭/註記都帶錨點,且 ⊆ 該 K 的錨點
D3 節點字 ≤18 CJK、箭頭標籤 ≤6 CJK;術語(jargon.txt)出現在節點時,同卡文字須已說明(由 k_check jargon 規則保證)→ 此處只警告
D4 i.html 每圖都已嵌入對應卡片;SVG 有 role=img + title/desc
D5 Playwright 渲染 i.html:無 JS 錯誤、圖不水平溢出卡片
"""
import sys, re, json
from pathlib import Path

CJK = re.compile(r"[一-鿿]")
TYPES = {"flow", "loop", "hub", "chain"}


def main():
    run = Path(sys.argv[1]).resolve(); f, w = [], []
    K = {k["k"]: set(k["anchors"]) for k in json.loads((run / "K.json").read_text(encoding="utf-8"))["K"]}
    D = json.loads((run / "diagrams.json").read_text(encoding="utf-8"))
    ih = (run / "i.html").read_text(encoding="utf-8")
    jf = run / "jargon.txt" if (run / "jargon.txt").exists() else Path(__file__).with_name("jargon_common.txt")
    jargon = [x.strip() for x in jf.read_text().splitlines() if x.strip()]
    for d in D:
        k, did = d["k"], d["id"]
        if d["type"] not in TYPES: f.append(f"{did} type {d['type']}")
        if len(d["nodes"]) > 9: f.append(f"{did} nodes {len(d['nodes'])} > 9")
        if len(d["edges"]) > 12: f.append(f"{did} edges {len(d['edges'])} > 12")
        ids = {n["id"] for n in d["nodes"]}
        for u in d["nodes"] + d["edges"]:
            a = set(u.get("anchors", []))
            name = u.get("id") or f'{u.get("from")}->{u.get("to")}'
            if not a: f.append(f"{did} {name} no anchors")
            if a - K.get(k, set()): f.append(f"{did} {name} anchors outside {k}: {sorted(a - K[k])}")
        for ed in d["edges"]:
            if ed["from"] not in ids or ed["to"] not in ids: f.append(f"{did} edge refs unknown node")
            if ed.get("label") and len(CJK.findall(ed["label"])) > 6: f.append(f"{did} edge label too long: {ed['label']}")
        for n in d["nodes"]:
            if n.get("status") not in ("existing", "proposed", "hypothetical"): f.append(f"{did} node {n['id']} status missing/invalid (existing|proposed|hypothetical)")
            if len(CJK.findall(n["label"])) > 18: f.append(f"{did} node label too long: {n['label']}")
            for j in jargon:
                if j in n["label"]: w.append(f"WARN {did} node uses jargon 「{j}」— card text must explain it")
        if d.get("note") and not d.get("note_anchors"): f.append(f"{did} note without anchors")
        if f'data-diagram="{did}"' not in ih: f.append(f"{did} not embedded in i.html")
        fig = re.search(rf'<figure class="kdiagram" data-k="([^"]+)" data-diagram="{did}">', ih)
        if fig and fig.group(1) != k: f.append(f"{did} embedded in {fig.group(1)} not {k}")
    for m in re.finditer(r'<svg[^>]*class="kdiagram-svg"[^>]*>', ih):
        if 'role="img"' not in m.group(0): f.append("svg without role=img")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
        pg.on("pageerror", lambda x: errs.append(str(x)))
        pg.goto((run / "i.html").as_uri()); pg.wait_for_timeout(300)
        over = pg.evaluate("""() => [...document.querySelectorAll('figure.kdiagram')].filter(f => f.scrollWidth > f.clientWidth + 2).map(f => f.dataset.diagram)""")
        (run / "verify").mkdir(exist_ok=True); pg.screenshot(path=str(run / "verify/i_diagrams.png"), full_page=True)
        b.close()
    if over: f.append(f"overflow {over}")
    if errs: f.append(f"js errors {errs[:2]}")
    for x in w[:10]: print(x)
    for x in f[:30]: print("FAIL", x)
    print(f"diagrams={len(D)}", "PASS" if not f else f"{len(f)} failure(s)"); sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
