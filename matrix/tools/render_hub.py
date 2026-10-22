#!/usr/bin/env python3
"""四象限入口頁 index.html(確定性)。只列出實際存在的四個象限頁,不放其他素材。
用法: render_hub.py <run_dir>   讀 meta.json、K.json(選)、source.anchors.json
"""
import sys, json, html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ui

e = lambda s: html.escape(str(s), quote=True)
QUAD = [  # (檔名, 羅馬數字, 名稱, 座標, 一句用途)
    ("ii.html", "II", "理解過程", "完整 × 初學", "第一次讀：照講者的順序讀完整篇。"),
    ("i.html", "I", "建立入口", "重點 × 初學", "三分鐘看懂重點，再決定要深入哪裡。"),
    ("iii.html", "III", "追查與檢核", "完整 × 精通", "挑一句往外查到底：反白、註記、帶去查、再帶回來。"),
    ("iv.html", "IV", "交換與判斷", "重點 × 精通", "這場的重點，和其他場次的重點怎麼連。"),
]


def main():
    run = Path(sys.argv[1])
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8")) if (run / "meta.json").exists() else {}
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    K = json.loads((run / "K.json").read_text(encoding="utf-8"))["K"] if (run / "K.json").exists() else []
    title = meta.get("title", A["title"]); n = len(A["paragraphs"])
    cells = {}
    for f, r, name, axis, use in QUAD:
        if (run / f).exists():
            cells[r] = (f'<a class="cell" href="{f}"><span class="r">{r}</span><span class="axis">{axis}</span>'
                        f'<span class="name">{name}</span><span class="use">{use}</span></a>')
        else:
            why = "這場沒有做深讀：III 只給正在深讀的場次" if r == "III" else "尚未產出"
            cells[r] = f'<div class="cell empty"><span class="r">{r}</span><span class="axis">{axis}</span><span class="name">{name}</span><span class="use">{why}</span></div>'
    ks = "".join(f"<li><b>{e(k['k'])}</b>{e(k['point'])}</li>" for k in K)
    out = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}｜四象限學習輔助</title><style>
body{{margin:0}} .page{{max-width:1040px;margin:0 auto;padding:2.2rem 1.4rem 3rem}}
.kicker{{font-size:var(--fs-2);color:var(--ink-mute);letter-spacing:.08em}}
.lead{{color:var(--ink-soft);margin:.4rem 0 1.6rem}}
.grid{{display:grid;grid-template-columns:2.2rem 1fr 1fr;grid-template-rows:auto 1fr 1fr;gap:12px}}
.ax{{font-size:var(--fs-min);color:var(--ink-mute);display:flex;align-items:center;justify-content:center;letter-spacing:.1em}}
.ax.v{{writing-mode:vertical-rl}}
.cell{{display:flex;flex-direction:column;gap:.25rem;background:#fffdf9;border:1px solid var(--rule);border-radius:16px;padding:1.2rem 1.3rem;
  text-decoration:none;color:var(--ink);box-shadow:0 10px 26px -20px rgba(120,60,40,.45);transition:.18s;min-height:150px}}
a.cell:hover{{transform:translateY(-2px);border-color:var(--accent-soft);box-shadow:0 14px 30px -18px rgba(120,60,40,.55)}}
.cell .r{{font-family:var(--serif);font-size:1.9rem;font-weight:700;color:var(--accent);line-height:1}}
.cell .axis{{font-size:var(--fs-min);color:var(--ink-mute)}} .cell .name{{font-family:var(--serif);font-size:1.25rem;font-weight:700}}
.cell .use{{font-size:var(--fs-2);color:var(--ink-soft)}} .cell.empty{{opacity:.45;box-shadow:none}}
details{{margin-top:2rem;background:var(--paper-soft);border-radius:12px;padding:.8rem 1.1rem}}
details ol{{list-style:none;padding:0;margin:.6rem 0 0}} details li{{margin:.25rem 0}} details li{{font-size:var(--fs-2)}} details li b{{color:var(--accent);margin-right:.5rem;font-family:var(--serif)}}
.foot{{margin-top:1.6rem;font-size:var(--fs-min);color:var(--ink-mute)}}
@media(max-width:720px){{.grid{{grid-template-columns:1fr}} .ax{{display:none}}}}
</style></head><body><main class="page">
<div class="kicker ui">好學生矩陣（四象限學習輔助）</div>
<h1>{e(title)}</h1>
<div class="lead">{e(meta['speaker']) + '。' if meta.get('speaker') else ''}同一份逐字稿，依「要完整還是要重點」與「初學還是熟悉」分成四種讀法；每一頁都能點回原文段落。</div>
{ui.how('hub')}
<div style="height:1.4rem"></div>
<div class="grid ui"><div></div><div class="ax">完整（{n} 段）</div><div class="ax">重點{f"（{len(K)} 個）" if K else ""}</div>
<div class="ax v">初學</div>{cells['II']}{cells['I']}
<div class="ax v">精通</div>{cells['III']}{cells['IV']}</div>
{f'<details class="ui"><summary>這場的 {len(K)} 個重點（I 與 IV 共用）</summary><ol>{ks}</ol></details>' if K else ''}
<p class="foot ui">原文：{e(meta.get('published_ii', '')) and f'<a href="{e(meta["published_ii"])}">已出版的好學生筆記</a>'}</p>
</main></body></html>"""
    (run / "index.html").write_text(out, encoding="utf-8"); print("wrote", run / "index.html")


if __name__ == "__main__":
    main()
