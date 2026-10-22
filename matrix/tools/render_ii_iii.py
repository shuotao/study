#!/usr/bin/env python3
"""象限 II / III 完整原文頁(ii.html / iii.html)(確定性渲染;原文逐段照搬,LLM 只提供 claims.json)。

用法: render_ii_iii.py <run_dir> --mode ii|iii [--verify]
- 段落 id 與 source.anchors.json 一致(同一套切段規則)
- 圖片依 cleaned.md 原位置插入(相對連結到 session 目錄,只讀)
- claims.json: [{"claim": "...", "type": "主張|條件|例外|步驟|數字", "anchors": ["p0012", ...]}]
驗證: --verify 只檢查 ii.html/iii.html 每段文字與原文逐字相同(去標籤、去 ** 後比對)
"""
import os, sys, json, re, html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ui

IMG = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")
BOLD = re.compile(r"\*\*(.+?)\*\*")


def esc_md(s):
    return BOLD.sub(r"<strong>\1</strong>", html.escape(s, quote=False))


def render(run, mode="iii"):
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    sdir = Path(A["source"]).parent
    byid = iter(A["paragraphs"])
    claims = []
    cp = run / "claims.json"
    if mode == "iii" and cp.exists():
        claims = json.loads(cp.read_text(encoding="utf-8"))
    body, toc, started, last_pid, pending = [], [], False, None, []
    rel = os.path.relpath(sdir, run).replace(os.sep, "/") + "/"   # images stay in the session dir (read-only)
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8")) if (run / "meta.json").exists() else {}
    spk = json.loads((run / "speakers.json").read_text(encoding="utf-8"))["paragraphs"] if (run / "speakers.json").exists() else {}
    pub = meta.get("published_ii", "")   # 沒有就不放連結(不猜網址)
    TYPE = {"主張": "claim", "條件": "condition", "例外": "exception", "步驟": "step", "數字": "number"}
    for ln in Path(A["source"]).read_text(encoding="utf-8").splitlines():
        s = ln.rstrip()
        if not s.strip() or (s.startswith("# ") and not s.startswith("## ")):
            continue
        if s.startswith("## "):
            started = True; last_pid = None
            sid = f"s{len(toc)+1}"; toc.append((sid, s[3:]))
            body.append(f'<h2 id="{sid}">{html.escape(s[3:])}</h2>'); continue
        if s.startswith("### "):
            body.append(f"<h3>{html.escape(s[4:])}</h3>"); last_pid = None; continue
        m = IMG.match(s)
        if not started and not m:
            continue
        if m:
            fig = (f'<img loading="lazy" src="{rel}{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}">'
                   f'<figcaption>{html.escape(m.group(1))}</figcaption></figure>')
            if last_pid:
                body.append(f'<figure data-after="{last_pid}">' + fig)
            else:
                pending.append(len(body)); body.append(fig)
            continue
        p = next(byid)
        assert p["text"] == s, f"anchor drift at {p['id']}"
        for i in pending:
            body[i] = f'<figure data-before="{p["id"]}">' + body[i]
        pending = []; last_pid = p["id"]
        who = spk.get(p["id"], {}).get("who", "speaker")
        txt = esc_md(s)
        if who in ("mixed", "uncertain"):   # uncertain:保守處理,候選片段標「可能為聽眾」
            info = spk[p["id"]]
            spans = info.get("audience_spans", []) if who == "mixed" else info.get("candidate_audience_spans", [])
            title = "聽眾發言" if who == "mixed" else "可能為聽眾發言"
            for span in spans:
                es = esc_md(span)
                if es in txt: txt = txt.replace(es, f'<span class="aud-span" title="{title}">{es}</span>', 1)
        cls = ' class="aud"' if who == "audience" else ""
        tag = '<span class="aud-tag">聽眾</span>' if who == "audience" else ""
        body.append(f'<p id="{p["id"]}"{cls} data-sha1="{p["sha1"][:12]}"><a class="pid" href="#{p["id"]}">{p["id"]}</a>{tag}{txt}</p>')
    TN = {"主張": "主張", "條件": "條件", "例外": "例外", "步驟": "步驟", "數字": "數字"}
    rows = "".join(
        f'<li data-type="{TYPE.get(c["type"], c["type"])}" data-anchors="{" ".join(c["anchors"])}" tabindex="0">'
        f'{ui.tag("type", c["type"])}{ui.tag("aud") if c.get("speaker") == "audience" else ""}'
        f'<span class="ct">{html.escape(c["claim"])}</span>{ui.sup(c["anchors"], base="")}</li>' for c in claims)
    types = [t_ for t_ in TN if any(c["type"] == t_ for c in claims)]
    chips = "".join(f'<button type="button" data-f="{TYPE[t_]}">{t_}（{sum(c["type"] == t_ for c in claims)}）</button>' for t_ in types)
    tocs = "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in toc)
    title = meta.get("title") or A["title"]
    if mode == "ii":
        lead = (f"講者的原話，一段不漏（{len(A['paragraphs'])} 段），依講者的順序排列。"
                + (f'也可以讀<a href="{pub}">已出版的好學生筆記</a>。' if pub else ""))
    else:
        lead = ("原文逐段照錄。反白任何一句，可以寫註記、帶去 Claude 或 Google 往外查，再把查到的貼回來。"
                "註記只存在你的瀏覽器，不會改動原文；要保存時匯出成 Markdown。")
    topics = json.loads((run / "topics.json").read_text(encoding="utf-8")) if mode == "iii" and (run / "topics.json").exists() else []
    KQ = {"unsupported": "沒給依據", "hedged": "講者保留語氣", "relayed": "轉述他人", "unclear": "錄音不清",
          "absent": "原文未提", "ext": "需外部核對", "gaps": "原文未提", "deep": "值得深挖"}
    Kt = {}
    if (run / "i.json").exists():
        Kt = {x["k"]: re.sub(r"〔補述：.*?〕", "", x["headline"]) for x in json.loads((run / "i.json").read_text(encoding="utf-8"))["items"]}
    tgroups = []
    for k in dict.fromkeys(x["k"] for x in topics):
        items = "".join(
            f'<li data-refs="{" ".join(x["refs"])}">{ui.tag("ask", KQ.get(x["kind"], x["kind"]))}'
            + (f'<q>{html.escape(x["quote"])}</q>' if x.get("quote") else "")
            + f'<span class="tt">{html.escape(x["text"])}</span>{ui.sup(x["refs"], base="")}'
            + '<span class="acts"><button type="button" class="t-show">標出原文</button><button type="button" class="t-ask">問 Claude</button></span></li>'
            for x in topics if x["k"] == k)
        tgroups.append(f'<details{" open" if not tgroups else ""}><summary><b>{k}</b> {html.escape(Kt.get(k, ""))}<span class="n">{sum(x["k"] == k for x in topics)}</span></summary><ul class="topics">{items}</ul></details>')
    css = """.n-page.wide{max-width:1240px} .mode-ii .n-page.wide{max-width:1040px}
.mode-iii .text figure img{max-height:300px;width:auto}
.layout{display:grid;gap:2.4rem;align-items:start}
.mode-ii .layout{grid-template-columns:220px minmax(0,720px);justify-content:center}
.mode-iii .layout{grid-template-columns:minmax(0,1fr) 400px}
.toc,.side{position:sticky;top:4.2rem;max-height:calc(100vh - 5rem);overflow:auto;font-family:var(--sans)}
.toc h2,.side h2{font-size:var(--fs-2)!important;color:var(--ink-mute)!important;font-family:var(--sans)!important;letter-spacing:.12em;margin:.2rem 0 .5rem}
.toc ol{list-style:none;padding:0;margin:0;counter-reset:t}.toc li{font-size:var(--fs-2);margin:.35rem 0;line-height:1.5}
.toc a{text-decoration:none;color:var(--ink-soft)}.toc a:hover{color:var(--accent)}
.text h2{font-size:1.35rem;border-top:1px solid var(--rule);padding-top:1.4rem;margin-top:2.6rem;scroll-margin-top:4.5rem}
.text h3{font-size:1.1rem;margin-top:1.6rem}
.text p{margin:.9rem 0;scroll-margin-top:5rem}
.mode-ii .text p{line-height:2}
.mode-ii .pid{display:none}
.text figure{margin:1.2rem 0}.text figcaption{font-size:var(--fs-min);color:var(--ink-mute)}
.rail .tools{display:flex;flex-direction:column;gap:.6rem;margin-bottom:.8rem}
.rail .chips{display:flex;flex-wrap:wrap;gap:.35rem}.rail .chips button{padding:.2rem .75rem;font-size:var(--fs-min)}
.rail .count{font-size:var(--fs-min);color:var(--ink-mute)}
#claims{list-style:none;padding:0;margin:0}
#claims li{font-size:var(--fs-2);line-height:1.7;padding:.6rem .7rem;border-bottom:1px solid var(--rule);cursor:pointer;border-radius:8px}
#claims li:hover,#claims li.on{background:var(--paper-soft)}
#claims .ct{color:var(--ink)}
@media(max-width:1000px){.mode-ii .layout,.mode-iii .layout{grid-template-columns:1fr}.toc,.side{position:static;max-height:none}}"""
    css += """
.rail{position:sticky;top:4.2rem;max-height:calc(100vh - 5rem);display:flex;flex-direction:column;font-family:var(--sans)}
.tabs{display:flex;gap:.3rem;border-bottom:1px solid var(--rule);margin-bottom:.6rem}
.tabs button{border:0!important;border-radius:0!important;background:none!important;color:var(--ink-mute)!important;padding:.45rem .7rem;border-bottom:2px solid transparent!important}
.tabs button:hover{color:var(--accent)!important}
.tabs button[aria-selected=true]{color:var(--accent)!important;border-bottom-color:var(--accent)!important}
.pane{overflow:auto;padding-right:.3rem} .pane[hidden]{display:none}
.pane details{border-bottom:1px solid var(--rule);padding:.3rem 0} .pane summary{color:var(--ink);font-size:var(--fs-2);padding:.3rem 0}
.pane summary b{color:var(--accent);margin-right:.3rem;font-family:var(--serif)} .pane summary .n{float:right;color:var(--ink-mute);font-size:var(--fs-min)}
.topics{list-style:none;padding:0;margin:.2rem 0 .4rem} .topics li{font-size:var(--fs-2);line-height:1.7;padding:.5rem 0;border-top:1px dashed var(--rule)}
.topics q{display:block;color:var(--accent-ink);margin:.15rem 0}
.acts{display:flex;gap:.4rem;margin-top:.35rem} .acts button,.ann button{font-size:var(--fs-min);padding:.15rem .7rem}
.empty{color:var(--ink-mute);font-size:var(--fs-2);background:var(--paper-soft);border-radius:10px;padding:.8rem 1rem}
.ann{border:1px solid var(--rule);border-left:3px solid var(--accent);border-radius:8px;background:#fffdf9;padding:.6rem .8rem;margin:0 0 .7rem}
.ann blockquote{margin:0 0 .4rem;font-size:var(--fs-2);cursor:pointer;font-family:var(--serif)} .ann .src{font-size:var(--fs-min);color:var(--ink-mute)}
.ann label{display:block;font-size:var(--fs-min);color:var(--ink-mute);margin:.45rem 0 .15rem}
.ann textarea,.ann input,.ann select{width:100%;font-family:var(--sans);font-size:var(--fs-2)} .ann textarea{min-height:3.2em;resize:vertical}
.ann .row{display:flex;gap:.4rem;margin-top:.5rem;flex-wrap:wrap}
.ann.flash{box-shadow:0 0 0 3px var(--hl)}
.bar{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.4rem}
mark.ann-m{background:#f3dccd;color:inherit;border-bottom:2px solid var(--accent);border-radius:2px;cursor:pointer;padding:0 .05em}
#selbar{position:fixed;z-index:80;display:none;gap:.25rem;background:var(--ink);border-radius:10px;padding:.3rem;box-shadow:0 8px 24px -10px rgba(0,0,0,.5)}
#selbar button{background:none!important;border:0!important;color:#f7f1e8!important;font-size:var(--fs-2);padding:.3rem .7rem;border-radius:7px!important}
#selbar button:hover,#selbar button:focus-visible{background:var(--accent)!important}
@media(max-width:1000px){.rail{position:static;max-height:none}}"""
    side = ("" if mode == "ii" else
            f'''<aside class="rail ui" aria-label="深挖工具">
<div class="tabs" role="tablist"><button type="button" role="tab" data-p="notes">我的註記（<span id="ann-n">0</span>）</button><button type="button" role="tab" data-p="topics">深挖題目（{len(topics)}）</button>{f'<button type="button" role="tab" data-p="claims">主張（{len(claims)}）</button>' if claims else ""}</div>
<div class="pane" id="pane-notes" role="tabpanel"><div id="anns"></div>
<div class="empty" id="ann-empty">反白原文中任何一句，選「註記」或「問 Claude」，就會出現在這裡。查到的東西貼回這張註記，跟原文放在一起對照。</div>
<div class="bar"><button type="button" id="ann-export">匯出註記（Markdown）</button><button type="button" id="ann-clear">清除全部註記</button></div></div>
<div class="pane" id="pane-topics" role="tabpanel" hidden>{"".join(tgroups) or '<div class="empty">這場還沒有整理深挖題目。可以直接反白原文開始。</div>'}</div>
<div class="pane" id="pane-claims" role="tabpanel" hidden><div class="tools">
<input type="search" id="q" placeholder="搜尋主張或原文" aria-label="搜尋主張或原文">
<div class="chips"><button type="button" data-f="" class="on">全部（{len(claims)}）</button>{chips}</div>
<div class="count" id="count"></div></div><ol id="claims">{rows}</ol></div></aside>
<div id="selbar" role="toolbar" aria-label="對選取文字"><button type="button" data-a="note">註記</button><button type="button" data-a="claude">問 Claude</button><button type="button" data-a="google">Google</button><button type="button" data-a="copy">複製引文</button></div>''')
    ctx = json.dumps({"key": f"n.iii.{run.name}", "title": title, "speaker": meta.get("speaker", ""), "run": run.name}, ensure_ascii=False)
    js = ("" if mode == "ii" else "<script>const CTX=" + ctx + ";\n" + (Path(__file__).with_name("assets") / "iii.js").read_text(encoding="utf-8") + "</script>")
    return (ui.head(f"{'II 理解過程' if mode == 'ii' else 'III 追查與檢核'}｜{title}", css)
            + f'<body class="mode-{mode}"><main class="n-page{" wide" if mode == "iii" else " wide"}">'
            + ui.masthead(mode, title, lead)
            + '<div class="layout">'
            + (f'<nav class="toc ui"><h2>目錄</h2><ol>{tocs}</ol></nav>' if mode == "ii" else "")
            + f'<div class="text">{"" if mode == "ii" else f"<details class=ui><summary>目錄（{len(toc)} 節）</summary><ol>{tocs}</ol></details>"}'
            + "\n".join(body) + "</div>" + side + "</div>"
            + ui.nextbox(mode, lambda f_: (run / f_).exists()) + js + "</main></body></html>")


def verify(run, name="iii.html"):
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    t = (run / name).read_text(encoding="utf-8")
    bad = 0
    for p in A["paragraphs"]:
        m = re.search(rf'<p id="{p["id"]}"[^>]*><a class="pid"[^>]*>{p["id"]}</a>(.*?)</p>', t, re.S)
        got = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r'<span class="aud-tag">聽眾</span>', "", m.group(1)))) if m else None
        if got != BOLD.sub(r"\1", p["text"]):
            bad += 1; print("MISMATCH", p["id"])
    print(f"verbatim {len(A['paragraphs'])-bad}/{len(A['paragraphs'])}", "PASS" if not bad else "FAIL")
    return bad == 0


if __name__ == "__main__":
    run = Path(sys.argv[1])
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "iii"
    name = "ii.html" if mode == "ii" else "iii.html"
    if "--verify" in sys.argv:
        sys.exit(0 if verify(run, name) else 1)
    (run / name).write_text(render(run, mode), encoding="utf-8")
    print("wrote", run / name); sys.exit(0 if verify(run, name) else 1)
