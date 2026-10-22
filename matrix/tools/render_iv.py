#!/usr/bin/env python3
"""象限 IV「交換與判斷」= 廣度:這場的重點卡和其他場次的重點卡怎麼連(確定性產生器)。
用法: render_iv.py <run_dir>
讀 K.json、i.json(標題)、links/links.json(判斷步驟寫的關聯與排除)、vault.py 的筆記命名。
三層由遠到近(assets/iv.js):場次網(環形,其他場次排成一圈)→ 兩場對照(雙欄連線)→ 卡片圖譜(力導向,深度 1/2)。
欄位式平面圖撐不過三場以上,所以第一層只畫「場次」,卡片層級只在兩場對照與局部圖譜出現。
深度的追問(原 IV 的「值得追問」)已移到 III。
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ui, vault
from ui import e

TYPE_C = {"呼應": "#4a7a52", "延伸": "#a8442a", "實例": "#6a5a9a", "對照": "#3b6e8f", "不同看法": "#a8650a"}


def main():
    run = Path(sys.argv[1]).resolve(); N = run.parent.parent
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    C = vault.cards(); L = json.loads((N / "links/links.json").read_text(encoding="utf-8"))
    gen = meta.get("genealogy", "")                     # 只和同一族譜的場次比對;別的族譜不出現在這頁
    C = {cid: c for cid, c in C.items() if c["gen"] == gen}
    L = {k: [x for x in L[k] if x["a"] in C and x["b"] in C] for k in ("links", "excluded")}
    mine = [cid for cid in C if C[cid]["run"] == run.name]
    others = sorted({C[c]["run"] for c in C} - {run.name})
    rel = {cid: [(x, x["b"] if x["a"] == cid else x["a"]) for x in L["links"] if cid in (x["a"], x["b"])] for cid in mine}
    exc = [x for x in L["excluded"] if x["a"] in mine or x["b"] in mine]
    n_links = sum(len(v) for v in rel.values())
    linked_runs = {C[o]["run"] for v in rel.values() for _, o in v}

    sessions = [{"run": r, "label": json.loads((N / "runs" / r / "meta.json").read_text(encoding="utf-8")).get("label", r),
                 "title": json.loads((N / "runs" / r / "meta.json").read_text(encoding="utf-8")).get("title", r)} for r in sorted({C[c]["run"] for c in C})]
    data = {"here": run.name, "sessions": sessions,
            "cards": [{"id": cid, "run": c["run"], "k": c["k"], "h": e(c["headline"])} for cid, c in C.items()],
            "links": [{"a": x["a"], "b": x["b"], "t": x["type"], "why": e(x["why"])} for x in L["links"]], "colors": TYPE_C}
    legend = "".join(f'<span class="lg" style="--c:{c}">{t}</span>' for t, c in TYPE_C.items())
    by_run = {}
    cards = []
    for cid in mine:
        c = C[cid]
        items = "".join(f'''<li><span class="rt" style="--c:{TYPE_C[x["type"]]}">{x["type"]}</span><a href="../{C[o]["run"]}/iv.html#{C[o]["k"]}"><b>{e(C[o]["label"])} {C[o]["k"]}</b> {e(C[o]["headline"])}</a><p>{e(x["why"])}</p></li>''' for x, o in sorted(rel[cid], key=lambda z: C[z[1]]["label"]))
        empty = (f'<p class="none">已比對其他 {len(others)} 場，沒有找到真正相關的重點。</p>' if others
                 else f'<p class="none">「{e(gen)}」族譜裡目前沒有其他場次可以比對。</p>')
        obs = "obsidian://open?path=" + __import__("urllib.parse").parse.quote(str(vault.V / c["label"] / f'{c["name"]}.md'))
        more = (c["i"] or {}).get("more") or c["anchors"][:1]
        cards.append(f'''<section class="n-card" id="{c["k"]}" data-k="{c["k"]}" data-anchors="{" ".join(c["anchors"])}">
<header><span class="kn">{c["k"]}</span><h2>{e(c["headline"])}</h2><span class="cnt">{len(rel[cid])} 條關聯</span></header>
<p class="pt">{e(c["point"])}</p>
{f'<ul class="rels">{items}</ul>' if items else empty}
<div class="go"><a href="{obs}">在 Obsidian 開啟這張卡</a>{"".join(f'<a href="ii.html#{a}">讀這場的原文</a>' for a in more[:1])}</div>
</section>''')
    exc_html = "".join(f'<li><b>{e(C[x["a"]]["label"])} {C[x["a"]]["k"]}</b> ✕ <b>{e(C[x["b"]]["label"])} {C[x["b"]]["k"]}</b>：{e(x["why"])}</li>' for x in exc)
    css = """.n-page.wide{max-width:1160px}
.vt,.dp{display:flex;gap:.4rem;margin:.2rem 0 .8rem;flex-wrap:wrap}
.vt button[aria-pressed=true],.dp button[aria-pressed=true]{background:var(--accent)!important;color:#fff!important;border-color:var(--accent)!important}
.net{background:#fffdf9;border:1px solid var(--rule);border-radius:16px;padding:1rem 1.2rem 1.2rem;margin:0 0 1.6rem}
.net h2{font-size:var(--fs-body);margin:.2rem 0 .3rem}
.net .hint{font-family:var(--sans);font-size:var(--fs-2);color:var(--ink-mute);margin:0 0 .4rem}
#ring svg,#graph svg{display:block;width:100%;font-family:var(--sans)}
.chord{fill:none;stroke:#d9cfc0;opacity:.55} .chord.hl{stroke:var(--ink-soft);opacity:.9}
.spoke{stroke:#c9b8a6} .spoke.on{stroke:var(--accent)}
.sn{cursor:pointer} .sn circle{fill:#fffdf9;stroke:var(--ink-soft);stroke-width:1.6} .sn.zero circle{stroke:#c9bfb0;stroke-dasharray:3 3}
.sn.on circle{fill:var(--hl);stroke:var(--accent);stroke-width:2.6} .sn:hover circle,.sn:focus-visible circle{stroke:var(--accent)} .sn:focus{outline:none}
.sl{font-size:15px;fill:var(--ink);font-weight:600} .sc{font-size:14px;fill:var(--ink-mute)} .sn.zero .sl{fill:var(--ink-mute);font-weight:400}
.center circle{fill:var(--accent)} .center text{fill:#fff;font-size:16px;font-weight:700}
#pair{margin-top:.8rem;border-top:1px solid var(--rule);padding-top:.8rem}
#pair-h{font-family:var(--sans);font-size:var(--fs-2);color:var(--ink-soft);margin:.2rem 0 .7rem}
.map{position:relative;display:grid;grid-template-columns:1fr 1fr;gap:0 5rem}
.map svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}
.col h3{font-size:var(--fs-2)!important;color:var(--ink-mute)!important;font-family:var(--sans)!important;margin:0 0 .5rem;font-weight:600}
.node{position:relative;z-index:1;display:block;background:#fffdf9;border:1px solid var(--rule);border-radius:8px;padding:.35rem .7rem;margin:0 0 .45rem;
  font-family:var(--sans);font-size:var(--fs-2);line-height:1.45;color:var(--ink);text-decoration:none}
.node b{color:var(--accent);margin-right:.4rem;font-family:var(--serif)} .node.here{border-color:var(--accent-soft);background:var(--hl)} .node.dim{color:var(--ink-mute);background:#fbf8f3;border-style:dashed} .node.dim b{color:var(--ink-mute)}
#pair-list{list-style:none;padding:0;margin:.8rem 0 0} #pair-list li{border-top:1px solid var(--rule);padding:.6rem 0;font-family:var(--sans);font-size:var(--fs-2)}
#pair-list p{margin:.2rem 0 0;color:var(--ink-soft)} #pair-list a{text-decoration:none}
.gn{cursor:pointer} .gn circle{stroke:#fff;stroke-width:1.5} .gl{font-size:14px;fill:var(--ink-soft);paint-order:stroke;stroke:#fffdf9;stroke-width:4px}
.gk{font-size:14px;fill:#fff;font-weight:700;pointer-events:none} .gl.hide{display:none} .gl.hide.show{display:inline} .labels{pointer-events:none} .gn.dim{opacity:.15} #g-info{font-family:var(--sans);font-size:var(--fs-2);min-height:1.6em;color:var(--ink)}
#g-count{font-family:var(--sans);font-size:var(--fs-min);color:var(--ink-mute)}
.lgs{display:flex;flex-wrap:wrap;gap:.4rem 1rem;font-family:var(--sans);font-size:var(--fs-2);color:var(--ink-soft);margin:.6rem 0 0}
.lg::before{content:"";display:inline-block;width:1.6em;height:3px;background:var(--c);vertical-align:middle;margin-right:.35rem;border-radius:2px}
.rt{display:inline-block;font-family:var(--sans);font-size:var(--fs-min);color:#fff;background:var(--c);border-radius:6px;padding:0 .5rem;margin-right:.5rem;white-space:nowrap}
.cnt{font-family:var(--sans);font-size:var(--fs-min);color:var(--ink-mute)}
.pt{color:var(--ink-soft)} .rels{list-style:none;padding:0!important;margin-top:.8rem!important}
.rels li{border-top:1px solid var(--rule);padding:.65rem 0 .2rem;margin:0!important}
.rels a{text-decoration:none;font-family:var(--sans);font-size:var(--fs-2)} .rels p{margin:.25rem 0 0;font-size:var(--fs-2);color:var(--ink-soft)}
.none{color:var(--ink-mute);font-family:var(--sans);font-size:var(--fs-2)}
.rk{list-style:none;padding:0;margin:0} .rk li{margin:.3rem 0}
.rk button{display:grid;grid-template-columns:7.5em 1fr auto;gap:.6rem;align-items:center;width:100%;text-align:left;border-radius:10px!important;padding:.4rem .7rem;color:var(--ink)!important}
.rk .bar{height:6px;background:var(--accent-soft);border-radius:3px;min-width:2px} .rk button.on{background:var(--hl)!important;border-color:var(--accent)!important;color:var(--ink)!important}
.exc{margin-top:2rem} .exc li{font-size:var(--fs-2);color:var(--ink-soft);margin:.3rem 0}
@media(max-width:820px){.map{grid-template-columns:1fr;gap:.6rem}.map svg{display:none}}"""
    js = ("<script>window.IV=" + json.dumps(data, ensure_ascii=False) + ";\n"
          + (Path(__file__).with_name("assets") / "iv.js").read_text(encoding="utf-8") + "</script>")
    empty_solo = f'<p class="none">「{e(gen)}」族譜裡目前沒有其他場次可以比對。</p>'
    if not others:                                      # 族譜只有這一場:不放場次網、卡片圖譜與其 JS
        lead = (f"這場屬於「{e(gen)}」族譜，族譜裡目前只有這一場，沒有其他場次可以連。"
                f"下面先列出這場的 {len(mine)} 張重點卡。")
        out = (ui.head(f"IV 交換與判斷｜{meta.get('title', '')}", css) + '<body><main class="n-page wide" data-view="breadth" data-solo="1">'
               + ui.masthead("iv", "這場的重點，和其他場次怎麼連", lead, how_key="iv-solo")
               + "".join(c.replace('<span class="cnt">0 條關聯</span>', "").replace(empty_solo, "") for c in cards)   # 頁首已說明,卡上不再重複
               + ui.nextbox("iv", lambda f: (run / f).exists()) + "</main></body></html>")
        (run / "iv.html").write_text(out, encoding="utf-8")
        print("wrote", run / "iv.html", f"solo genealogy={gen}")
        return
    lead = (f"這場 {len(mine)} 張重點卡，和其他 {len(others)} 場比對後，找到 {n_links} 條關聯、連到 {len(linked_runs)} 場；"
            f"另有 {len(exc)} 組只是字面相似，已排除並寫明原因。")
    out = (ui.head(f"IV 交換與判斷｜{meta.get('title', '')}", css) + '<body><main class="n-page wide" data-view="breadth">'
           + ui.masthead("iv", "這場的重點，和其他場次怎麼連", lead)
           + '<section class="net ui" aria-label="關聯網">'
             '<div class="vt" role="group" aria-label="檢視"><button type="button" data-v="sessions" aria-pressed="true">場次網</button><button type="button" data-v="graph" aria-pressed="false">卡片圖譜</button></div>'
             '<div id="v-sessions"><p class="hint">中間是這一場，外圈是其他場次；線越粗、圓越大，關聯越多。點一個場次，下面會並排比對兩場的重點卡。細弧線是其他場次彼此之間的關聯。</p>'
             '<div id="ring"><svg role="img" aria-label="場次關聯網"></svg></div>'
             '<div id="pair"><div id="pair-h"></div><div class="map"></div><ul id="pair-list"></ul></div></div>'
             '<div id="v-graph" hidden><p class="hint">每個點是一張重點卡，顏色代表場次；同一場的卡會聚在一起。滑過一點看它連到誰，點下去跳到那張卡。</p>'
             '<div class="dp" role="group" aria-label="深度"><button type="button" data-d="1" aria-pressed="true">直接相連</button><button type="button" data-d="2" aria-pressed="false">再往外一層</button><span id="g-count"></span></div>'
             '<div id="g-info"></div><div id="graph"><svg role="img" aria-label="卡片圖譜"></svg></div></div>'
           + f'<div class="lgs">{legend}</div></section>'
           + "".join(cards)
           + (f'<details class="exc ui"><summary>字面相似、但已排除的 {len(exc)} 組</summary><ul>{exc_html}</ul></details>' if exc else "")
           + ui.nextbox("iv", lambda f: (run / f).exists()) + js + "</main></body></html>")
    (run / "iv.html").write_text(out, encoding="utf-8")
    print("wrote", run / "iv.html", f"links={n_links} excluded={len(exc)}")


if __name__ == "__main__":
    main()
