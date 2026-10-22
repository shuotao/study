#!/usr/bin/env python3
"""象限 I 確定性產生器:i.json → i.html(重點清單 + 卡片 + 讀原文連結)。圖解由 render_diagram.py 之後嵌入。
LLM 只寫 i.json(內容判斷);版面、元件、字級全由本工具與 tools/ui.py 產生,與 II/III/IV 共用。

i.json = {"title":"這場在講：…一句話","items":[{
  "k":"K1","headline":"白話標題","anchors":["p0024",…],          # ⊆ K.json 該點錨點
  "paras":[{"text":"短句","gloss":{"term":"LLM","text":"LLM＝…","after":"選填"}}],  # 接在 after(預設 term)第一次出現後(§V0.4a)
  "more":["p0025"]}]}                                               # 「讀原文」連到 ii.html 的段落
"""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ui
from ui import e


def para_html(p):
    t = e(p["text"]); g = p.get("gloss")
    if g:
        span = f'<span class="supp" data-term="{e(g["term"])}">〔補述：{e(g["text"])}〕</span>'
        at = e(g.get("after") or g["term"])          # after:補述接在哪段字之後(預設 term 第一次出現處)
        t = t.replace(at, at + span, 1) if at in t else t + span
    return f"<p>{inline_supp(t)}</p>"


def inline_supp(t):
    """標題或句子裡直接寫的〔補述：…〕也渲染成補述樣式(舊頁遷移來的標題補述)。"""
    return re.sub(r"〔補述：(.*?)〕", r'<span class="supp">〔補述：\1〕</span>', t)


def main():
    run = Path(sys.argv[1])
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    D = json.loads((run / "i.json").read_text(encoding="utf-8"))
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    sec = {p["id"]: p.get("section", "") for p in A["paragraphs"]}
    items = D["items"]
    cards = []
    for it in items:
        k = it["k"]
        links = "".join(f'<a href="ii.html#{r}" title="原文 {r}">讀原文：{e(sec.get(r) or r)}</a>' for r in it.get("more", []))
        cards.append(f'''<article class="n-card" id="{k}" data-k="{k}" data-anchors="{" ".join(it["anchors"])}">
<header><span class="kn">{k}</span><h2>{inline_supp(e(it["headline"]))}</h2></header>
{"".join(para_html(p) for p in it["paras"])}
<div class="go">{links}</div>
</article>''')
    index = "".join(f'<li><a href="#{it["k"]}"><b>{it["k"]}</b>{e(it["headline"])}</a></li>' for it in items)
    minutes = max(1, round(sum(len(p["text"]) for it in items for p in it["paras"]) / 400))
    lead = f'{len(items)} 個重點，約 {minutes} 分鐘。每張卡都能點回講者的原話。'
    out = (ui.head(f"I 建立入口｜{meta.get('title', '')}")
           + '<body><main class="n-page">'
           + ui.masthead("i", D["title"], e(lead))
           + f'<nav class="n-index ui" aria-label="重點清單"><h2>重點清單</h2><ul>{index}</ul></nav>'
           + "\n".join(cards)
           + ui.nextbox("i", lambda f: (run / f).exists())
           + "</main></body></html>")
    (run / "i.html").write_text(out, encoding="utf-8")
    print("wrote", run / "i.html", len(items), "cards")


if __name__ == "__main__":
    main()
