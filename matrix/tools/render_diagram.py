#!/usr/bin/env python3
"""象限 I 圖解產生器(確定性;版面規則仿 html-visualizer/diagram-design:≤9 節點、≤12 箭頭、
4px 網格、無陰影、圓角 8、強調色 ≤2、中文 ≥14px、圖例放下方)。不安裝外部程式。

用法: render_diagram.py <run_dir>          讀 diagrams.json → 寫 diagrams/<id>.svg + 嵌入 i.html
     render_diagram.py <run_dir> --no-embed
diagrams.json: [{"id":"d-k1","k":"K1","type":"flow|loop|hub|chain","title":"…","desc":"…",
  "nodes":[{"id":"n1","label":"…","sub":"…(選)","anchors":["p0007"],"accent":false,
            "status":"existing|proposed|hypothetical"}],   # 必填:現況/講者提議/假設情境(虛線/點線框,圖下自動加圖例)
  "edges":[{"from":"n1","to":"n2","label":"…(選)","anchors":["p0008"],"dashed":false}],
  "note":"…(選,圖下方小字,須有 note_anchors)","note_anchors":[]}]
"""
import sys, json, math, re, html
from pathlib import Path

W_BOX, H_BOX, GAP_X, GAP_Y, PAD = 176, 80, 56, 48, 24   # 三行字高度
INK, MUTED, LINE, ACCENT, FILL, ACC_FILL = "#2d2a26", "#7a7264", "#b8ae99", "#b34a2f", "#fffdf9", "#f7f1e8"   # 好學生筆記配色
e = lambda s: html.escape(s, quote=True)


def wrap(t, n=10):
    """依顯示寬度換行(CJK=1、拉丁字元≈0.55),拉丁字詞不從中間切斷(persona:Aut／oCAD)。"""
    import re as _re
    toks = _re.findall(r"[A-Za-z0-9.#+_-]+|\s+|.", t.strip())
    wid = lambda s: sum(0.55 if ord(c) < 128 else 1 for c in s)
    lines, cur = [], ""
    for tk in toks:
        if wid(cur + tk) > n and cur.strip():
            lines.append(cur.strip()); cur = tk.lstrip()
        else:
            cur += tk
    if cur.strip(): lines.append(cur.strip())
    return lines[:3] if len(lines) <= 3 else lines[:2] + [lines[2][:-1] + "…"]


def dagre_layout(d):
    """用 vendor/dagre 排版(flow/chain/loop);失敗回傳 None 改用內建版面。"""
    import subprocess, shutil
    js = Path(__file__).with_name("dagre_layout.cjs")
    if d["type"] == "hub" or not shutil.which("node") or not (js.parent.parent / "vendor/dagre/node_modules/dagre").exists():
        return None
    rank = "LR" if len(d["nodes"]) <= 2 else "TB"   # 卡片寬度下 3 個橫排字會太小
    spec = {"rankdir": rank, "nodes": [{"id": n["id"], "w": W_BOX, "h": H_BOX} for n in d["nodes"]],
            "edges": [{"from": e["from"], "to": e["to"], "lw": (15 * len(e["label"]) + 12) if e.get("label") else 0} for e in d["edges"]]}
    r = subprocess.run(["node", str(js)], input=json.dumps(spec), capture_output=True, text=True, timeout=30)
    if r.returncode: return None
    out = json.loads(r.stdout)
    return {k: (v["x"], v["y"]) for k, v in out["nodes"].items()}, out["w"], out["h"], out["edges"]


def layout(d):
    nodes, t = d["nodes"], d["type"]; pos = {}
    if t in ("flow", "chain"):
        per = min(3, len(nodes))   # 卡片兩欄寬約 560px:一列最多 3 個,超過蛇行換列(4 個一列會縮到字太小)
        for i, nd in enumerate(nodes):
            r, c = divmod(i, per)
            if r % 2 == 1: c = per - 1 - c          # 蛇行:第二列反向,箭頭不必回頭
            pos[nd["id"]] = (PAD + c * (W_BOX + GAP_X), PAD + r * (H_BOX + GAP_Y))
    elif t == "loop":
        n = len(nodes); R = max(120, n * 34)
        cx, cy = PAD + R + W_BOX / 2, PAD + R * 0.62 + H_BOX / 2
        for i, nd in enumerate(nodes):
            a = -math.pi / 2 + 2 * math.pi * i / n
            pos[nd["id"]] = (round((cx + R * math.cos(a) - W_BOX / 2) / 4) * 4, round((cy + R * 0.62 * math.sin(a) - H_BOX / 2) / 4) * 4)
    elif t == "hub":
        hub, sats = nodes[0], nodes[1:]; n = len(sats); R = 270
        cx, cy = PAD + R + W_BOX / 2, PAD + 150 + H_BOX / 2
        pos[hub["id"]] = (cx - W_BOX / 2, cy - H_BOX / 2)
        for i, nd in enumerate(sats):
            a = -math.pi / 2 + 2 * math.pi * i / n
            pos[nd["id"]] = (round((cx + R * math.cos(a) - W_BOX / 2) / 4) * 4, round((cy + 150 * math.sin(a) - H_BOX / 2) / 4) * 4)
    xs = [x for x, _ in pos.values()]; ys = [y for _, y in pos.values()]
    mx, my = min(xs) - PAD, min(ys) - PAD
    pos = {k: (x - mx, y - my) for k, (x, y) in pos.items()}
    w = max(x for x, _ in pos.values()) + W_BOX + PAD; h = max(y for _, y in pos.values()) + H_BOX + PAD
    return pos, w, h


def border_pt(x, y, tx, ty):
    """從方框中心朝 (tx,ty) 射出,與框邊的交點。"""
    cx, cy = x + W_BOX / 2, y + H_BOX / 2; dx, dy = tx - cx, ty - cy
    if dx == dy == 0: return cx, cy
    s = min((W_BOX / 2) / abs(dx) if dx else 1e9, (H_BOX / 2) / abs(dy) if dy else 1e9)
    return cx + dx * s, cy + dy * s


def svg(d):
    dl = dagre_layout(d)
    if dl: pos, w, h, dedges = dl
    else: (pos, w, h), dedges = layout(d), None
    nid = d["id"]; parts = []
    note_h = 28 if d.get("note") else 0
    # 圖例/註記寬度也算進畫布,避免被裁切(dagre 直排時畫布很窄)
    _sts = {n.get("status", "existing") for n in d["nodes"]}
    _leg_w = (sum(28 + 15 * len(t) + 24 for k, t in (("existing", "實線框＝講者描述的現況"), ("proposed", "虛線框＝講者的提議，尚未實施"),
                                                    ("hypothetical", "點線框＝講者的假設情境")) if k in _sts) + 2 * PAD) if _sts != {"existing"} else 0
    _note_w = 15 * len(d.get("note", "")) + 2 * PAD
    if max(_leg_w, _note_w) > w:
        shift = (max(_leg_w, _note_w) - w) / 2
        pos = {k: (x + shift, y) for k, (x, y) in pos.items()}
        if dedges: dedges = [{**e, "points": [[a + shift, b] for a, b in e["points"]]} for e in dedges]
        w = max(_leg_w, _note_w)
    leg_h = 0 if all(n.get("status", "existing") == "existing" for n in d["nodes"]) else 24
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h + note_h + leg_h:.0f}" role="img" '
                 f'aria-labelledby="{nid}-title {nid}-desc" class="kdiagram-svg" style="width:{w:.0f}px;max-width:none;height:auto;display:block;margin:0 auto">')
    parts.append(f'<title id="{nid}-title">{e(d["title"])}</title><desc id="{nid}-desc">{e(d.get("desc", d["title"]))}</desc>')
    parts.append(f'<defs><marker id="{nid}-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>')
    for ei, ed in enumerate(d["edges"]):
        (x1, y1), (x2, y2) = pos[ed["from"]], pos[ed["to"]]
        c1 = (x1 + W_BOX / 2, y1 + H_BOX / 2); c2 = (x2 + W_BOX / 2, y2 + H_BOX / 2)
        p1 = border_pt(x1, y1, *c2); p2 = border_pt(x2, y2, *c1)
        pts = dedges[ei]["points"] if dedges else None
        dash = ' stroke-dasharray="5 4"' if ed.get("dashed") else ""
        anc = " ".join(ed.get("anchors", []))
        href = f'ii.html#{ed["anchors"][0]}' if ed.get("anchors") else "#"
        parts.append(f'<a href="{href}" data-anchors="{anc}" data-edge="{e(ed["from"])}-{e(ed["to"])}">'
                     + (f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="none" stroke="{LINE}" stroke-width="1.6"{dash} marker-end="url(#{nid}-arr)"/>'
                        if pts else f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="{LINE}" stroke-width="1.6"{dash} marker-end="url(#{nid}-arr)"/>'))
        if ed.get("label"):
            mx, my = ((pts[len(pts) // 2][0], pts[len(pts) // 2][1]) if pts else ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2))
            lw = 15 * len(ed["label"]) + 12
            parts.append(f'<rect x="{mx - lw / 2:.1f}" y="{my - 12:.1f}" width="{lw}" height="22" rx="4" fill="#f7f1e8"/>'
                         f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" font-size="14" fill="{MUTED}">{e(ed["label"])}</text>')
        parts.append("</a>")
    for nd in d["nodes"]:
        x, y = pos[nd["id"]]; acc = nd.get("accent")
        anc = " ".join(nd["anchors"]); lines = wrap(nd["label"]) + ([nd["sub"]] if nd.get("sub") else [])
        st = nd.get("status", "existing")
        dash = {"proposed": ' stroke-dasharray="7 4"', "hypothetical": ' stroke-dasharray="2 4"'}.get(st, "")
        parts.append(f'<a href="ii.html#{nd["anchors"][0]}" data-anchors="{anc}" data-node="{e(nd["id"])}" data-status="{st}">'
                     f'<rect x="{x}" y="{y}" width="{W_BOX}" height="{H_BOX}" rx="8" fill="{"#f7f1e8" if st == "hypothetical" else FILL}" '
                     f'stroke="{ACCENT if acc else INK}" stroke-width="{2.2 if acc else 1.4}"{dash}/>')
        # 狀態角標:不只靠線型,文字直接標出(persona r2:點線/虛線難分、藍底被讀成「已定案」→ 強調只用框色,不用底色)
        tag = {"proposed": "提議", "hypothetical": "假設"}.get(st)
        if tag:
            parts.append(f'<rect x="{x + W_BOX - 42}" y="{y - 10}" width="38" height="20" rx="4" fill="#fff" stroke="{MUTED}" stroke-width="1"/>'
                         f'<text x="{x + W_BOX - 22}" y="{y + 4}" text-anchor="middle" font-size="14" fill="{MUTED}">{tag}</text>')
        y0 = y + H_BOX / 2 - (len(lines) - 1) * 9 + 5   # 置中(最多三行)
        for i, ln in enumerate(lines):
            sub = nd.get("sub") and i == len(lines) - 1
            parts.append(f'<text x="{x + W_BOX / 2}" y="{y0 + i * 19:.1f}" text-anchor="middle" font-size="{14 if sub else 15}" '
                         f'fill="{MUTED if sub else INK}">{e(ln)}</text>')
        parts.append("</a>")
    sts = [x for x in ("existing", "proposed", "hypothetical") if any(n.get("status", "existing") == x for n in d["nodes"])]
    LEG = {"existing": ("", "實線框＝講者描述的現況"), "proposed": ("7 4", "虛線框＝講者的提議，尚未實施"),
           "hypothetical": ("2 4", "點線框＝講者的假設情境")}
    if sts != ["existing"]:
        lx = PAD
        for x in sts:
            da, txt = LEG[x]
            parts.append(f'<rect x="{lx}" y="{h - 4 + note_h:.0f}" width="22" height="14" rx="3" fill="#fff" stroke="{INK}" stroke-width="1.4"'
                         + (f' stroke-dasharray="{da}"' if da else "") + f'/><text x="{lx + 28}" y="{h + 7 + note_h:.0f}" font-size="14" fill="{MUTED}">{txt}</text>')
            lx += 28 + 15 * len(txt) + 24
    if d.get("note"):
        parts.append(f'<text x="{PAD}" y="{h + 14:.0f}" font-size="14" fill="{MUTED}" data-anchors="{" ".join(d.get("note_anchors", []))}">{e(d["note"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def embed(run, diagrams):
    p = run / "i.html"; t = p.read_text(encoding="utf-8")
    t = re.sub(r'\s*<figure class="kdiagram"[^>]*>.*?</figure>', "", t, flags=re.S)   # 冪等:先清掉舊圖
    for d in diagrams:
        m = (re.search(rf'(<article[^>]*data-k="{d["k"]}"[^>]*>)(.*?)(\s*<div class="go")', t, re.S)
             or re.search(rf'(<article[^>]*data-k="{d["k"]}"[^>]*>)(.*?)(\s*<a [^>]*href="ii\.html)', t, re.S))
        if not m: raise SystemExit(f"card {d['k']} not found in i.html")
        fig = (f'\n<figure class="kdiagram" data-k="{d["k"]}" data-diagram="{d["id"]}">{svg(d)}'
               f'<figcaption>圖解：{e(d["title"])}（點節點讀原文）</figcaption></figure>')
        t = t[:m.end(2)] + fig + t[m.end(2):]
    p.write_text(t, encoding="utf-8")


def main():
    run = Path(sys.argv[1]); diagrams = json.loads((run / "diagrams.json").read_text(encoding="utf-8"))
    (run / "diagrams").mkdir(exist_ok=True)
    for d in diagrams:
        (run / "diagrams" / f'{d["id"]}.svg').write_text(svg(d), encoding="utf-8")
    if "--no-embed" not in sys.argv:
        embed(run, diagrams)
    print(f"rendered {len(diagrams)} diagrams", "(embedded)" if "--no-embed" not in sys.argv else "")


if __name__ == "__main__":
    main()
