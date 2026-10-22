"""四頁共用的版面元件(I / II / III / IV / 入口頁都從這裡取,改一處四頁一起變)。

設計語彙(樣式在 assets/theme.css 的「共用元件」段):
  how()      頁首「這頁怎麼讀」:三步,每頁依自己的讀法寫
  page()     共用 HTML 外殼(頁首 kicker + h1 + lead + how)
  sup()      出處上標:小數字、逗號分隔、點了跳原文(II/III/IV 一致)
  tag()      標籤:聽眾 / 講義 / 值得細讀 / 熟手可略 / 條件…(同一種長相)
  nextbox()  頁尾「讀完之後」:指向其他象限的下一步(四頁互相導流)
字級下限 14px 由 ui_check.py 機械檢查。
"""
import html

e = lambda s: html.escape(str(s), quote=True)

# 每頁的讀法(三步)。四頁讀法不同:II 線性、I 掃讀、III 查詢、IV 分流→精讀→帶走
HOW = {
    "ii": ["看目錄，知道這場分幾段", "照講者的順序讀下去", "卡住時，去 I 看這段的重點"],
    "i": ["先掃一遍下面的重點清單", "每張卡看標題、短文和圖解", "挑一張有興趣的，點「讀原文」深入"],
    "iii": ["反白一句有興趣的話，或從右側挑一個深挖題目", "寫註記，或帶去 Claude、Google 往外查", "把查到的貼回註記，對照原文判斷"],
    "iv": ["先看場次網：哪幾場和這場最相關", "點一個場次，並排比對兩場的重點卡", "想自由探索就切到卡片圖譜；有興趣的在 Obsidian 開啟"],
    # 族譜只有這一場(meta.json genealogy 沒有其他場次):不畫場次網,只列重點卡
    "iv-solo": ["這場所屬的族譜目前只有這一場，沒有其他場次可以連", "先讀下面的重點卡，知道這場講了哪幾件事", "想對某張卡往外深挖就去 III；之後同族譜有新場次，關聯會出現在這裡"],
    "hub": ["看自己是初學還是熟悉這個主題", "決定要讀完整還是只看重點", "點進對應的那一格"],
}
QUAD = {"ii": ("II", "理解過程", "完整 × 初學"), "i": ("I", "建立入口", "重點 × 初學"),
        "iii": ("III", "追查與檢核", "完整 × 精通"), "iv": ("IV", "交換與判斷", "重點 × 精通")}
# 讀完之後該去哪(依讀者的下一個動作,不是依頁碼)
NEXT = {
    "ii": [("i", "想先抓重點，再回來讀"), ("iii", "想針對某一句往外查到底")],
    "i": [("ii", "想照順序讀完整篇"), ("iv", "想看這些重點和其他場次怎麼連")],
    "iii": [("ii", "查完了，回到原文順著讀"), ("iv", "想看這個題目在其他場次怎麼講")],
    "iv": [("iii", "對某張卡想往外深挖"), ("ii", "回到這場的原文")],
}


def how(page, key=None):
    steps = "".join(f"<li>{e(s)}</li>" for s in HOW[key or page])
    return f'<section class="n-how ui" aria-label="這頁怎麼讀"><h2>這頁怎麼讀</h2><ol>{steps}</ol></section>'


def head(title, extra_css=""):
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>'
            f'<style>{extra_css}</style></head>')


def masthead(page, title, lead="", how_key=None):
    r, name, axis = QUAD[page]
    return (f'<header class="n-mast"><div class="n-kicker ui">象限 {r}　{name}（{axis}）</div>'
            f'<h1>{e(title)}</h1>{f"<div class=n-lead>{lead}</div>" if lead else ""}{how(page, how_key)}</header>')


def sup(refs, notes=None, base="iii.html"):
    """出處上標。notes 給了就用頁內流水號(IV);沒給就直接顯示段落編號(III 自己的頁內連結)。"""
    out = []
    for r in refs:
        if notes is not None:
            if r not in notes: notes.append(r)
            label = str(notes.index(r) + 1)
        else:
            label = r
        href = ("#aux-" + r) if r.startswith("h") else f"{base}#{r}"
        out.append(f'<a class="fn" href="{href}" data-ref="{r}" title="{"講義 " if r.startswith("h") else "原文 "}{r}">{label}</a>')
    if not out: return ""
    return f'<sup class="n-ref" data-anchors="{" ".join(refs)}">' + '<span class="sep">,</span>'.join(out) + "</sup>"


def tag(kind, text=None):
    TXT = {"aud": "聽眾", "aux": "講義", "deep": "值得細讀", "skim": "熟手可略", "maybe-aud": "可能為聽眾"}
    return f'<span class="n-tag {kind}">{e(text or TXT.get(kind, kind))}</span>'


def nextbox(page, exists):
    items = "".join(f'<li><a href="{q}.html"><b>{QUAD[q][0]}</b> {QUAD[q][1]}</a><span>{e(why)}</span></li>'
                    for q, why in NEXT[page] if exists(f"{q}.html"))
    return f'<footer class="n-next ui"><h2>讀完之後</h2><ul>{items}</ul></footer>' if items else ""
