#!/usr/bin/env python3
"""溯源位移檢查(observer_sheet_r1 §5 的實作)。只用標準庫。

用法: provenance_check.py <run_dir> --view sheet|ste_zh|ste_en|claims [--file F] [--window 3]
位移測試:單位裡缺在 cited 段落、卻出現在鄰近 ±W 段的 token = 位移證據。
  FAIL-NUMBER      數字不在 cited 段落
  FAIL-DISPLACED   位移的拉丁/數字 token ≥1,或位移的 CJK bigram ≥2(高頻 bigram 不計入 FAIL)
  FAIL-HEADING     缺的 token 只出現在區段標題(標題不是講者的話)
  WARN-DISPLACED / WARN-HEDGE-DROPPED / WARN-CAUSAL-ADDED
輸出 verify/provenance_<view>.json;任何 FAIL → exit 1。
"""
import sys, re, json, unicodedata
from html.parser import HTMLParser
from pathlib import Path

GLUE = set("的了是在和與及或把被給讓也都就還又很更最個這那其之")
STOP = {"the", "a", "an", "of", "to", "in", "on", "and", "or", "is", "are", "for", "with", "it", "you", "we", "that", "this", "be"}
HEDGES = ["如果", "假如", "只要", "除非", "一旦", "可能", "也許", "應該", "理想上", "通常", "大約", "大概",
          "我聽到", "另一場", "有人", "據說"]
CAUSAL = ["所以", "因此", "因為", "導致", "because", " so ", "therefore"]
ZHNUM = {"零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
ANCH = re.compile(r"\[\[(p\d{4})\]\]")


def zh2num(s):
    def conv(m):
        t = m.group(0)
        if t == "十": return "10"
        if "十" in t:
            a, _, b = t.partition("十")
            return str((ZHNUM.get(a, 1) if a else 1) * 10 + (ZHNUM.get(b, 0) if b else 0))
        return "".join(str(ZHNUM[c]) for c in t) if all(c in ZHNUM for c in t) and len(t) > 1 else t
    return re.sub(r"[一二兩三四五六七八九]?十[一二三四五六七八九]?", conv, s)


def norm(s):
    s = zh2num(unicodedata.normalize("NFKC", s).lower())
    return re.sub(r"\*\*", "", s)


def tokens(s):
    s = norm(s)
    lat = {t for t in re.findall(r"[a-z][a-z0-9.#+_-]*|\d+(?:\.\d+)?%?", s) if len(t) > 1 or t.isdigit()}
    lat = {t.rstrip(".") for t in lat if t not in STOP}
    cjk = set()
    for run in re.findall(r"[一-鿿]+", s):
        for i in range(len(run) - 1):
            bg = run[i:i + 2]
            if not (bg[0] in GLUE and bg[1] in GLUE):
                cjk.add(bg)
    return lat, cjk


class Cells(HTMLParser):
    """抽 [data-cell] 的文字與錨點(cell 內或外層 <a> 的 href / data-anchors)。"""
    def __init__(self):
        super().__init__(); self.stack = []; self.cells = []; self.a_stack = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        anchors = []
        if tag == "a":
            h = d.get("href", "")
            anchors = (d.get("data-anchors") or "").split() or ([h.split("#")[1]] if "iii.html#" in h else [])
            self.a_stack.append(anchors)
        if "data-cell" in d:
            outer = [a for lst in self.a_stack for a in lst]
            own = (d.get("data-anchors") or "").split()
            self.stack.append({"text": "", "anchors": own or outer, "tag": tag, "depth": 0})
        elif self.stack:
            if tag == "a" and anchors and not self.stack[-1]["anchors"]:
                self.stack[-1]["anchors"] = anchors
        for c in self.stack:
            if tag == c["tag"]: c["depth"] += 1
    def handle_endtag(self, tag):
        if tag == "a" and self.a_stack: self.a_stack.pop()
        if self.stack and tag == self.stack[-1]["tag"]:
            c = self.stack[-1]; c["depth"] -= 1
            if c["depth"] <= 0:
                self.cells.append(self.stack.pop())
    def handle_data(self, data):
        for c in self.stack: c["text"] += data


def units(run, view, f):
    if view == "sheet":
        p = Cells(); p.feed((run / (f or "sheet.html")).read_text(encoding="utf-8"))
        return [{"id": f"cell{i:03d}", "text": c["text"].strip(), "anchors": c["anchors"]}
                for i, c in enumerate(p.cells) if c["text"].strip() and not re.fullmatch(r"p\d{4}", c["text"].strip())]
    if view in ("ste_zh", "ste_en"):
        out = []
        for i, ln in enumerate((run / (f or f"{view}.md")).read_text(encoding="utf-8").splitlines()):
            s = ln.strip()
            if not s or s.startswith(("#", "<!--")): continue
            ids = ANCH.findall(s); body = ANCH.sub("", s).strip()
            sp = r"(?<=[。？！；])" if view == "ste_zh" else r"(?<=[.!?])\s+"
            for j, sent in enumerate(x for x in re.split(sp, body) if x.strip()):
                out.append({"id": f"L{i+1}s{j+1}", "text": sent.strip(), "anchors": ids})
        return out
    cl = json.loads((run / (f or "claims.json")).read_text(encoding="utf-8"))
    return [{"id": c.get("cid", str(i)), "text": c["claim"], "anchors": c["anchors"]} for i, c in enumerate(cl)]


def main():
    a = sys.argv[1:]; run = Path(a[0]).resolve(); view = a[a.index("--view") + 1]
    f = a[a.index("--file") + 1] if "--file" in a else None
    W = int(a[a.index("--window") + 1]) if "--window" in a else 3
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    P = A["paragraphs"]; idx = {p["id"]: i for i, p in enumerate(P)}
    ntext = [norm(p["text"]) for p in P]
    heads = norm(" ".join(A["sections"]) + " " + " ".join({p["subsection"] for p in P}))
    df = {}
    for t in ntext:
        for bg in tokens(t)[1]: df[bg] = df.get(bg, 0) + 1
    hi_freq = {bg for bg, n in df.items() if n / len(P) > 0.08}
    en = view == "ste_en"
    res, counts = [], {}
    for u in units(run, view, f):
        st = []
        if not u["anchors"] or any(x not in idx for x in u["anchors"]):
            st.append("FAIL-ANCHOR"); res.append({**u, "status": st}); continue
        ii = [idx[x] for x in u["anchors"]]
        cited = " ".join(ntext[i] for i in ii)
        near_ids = [P[i]["id"] for i in range(max(min(ii) - W, 0), min(max(ii) + W + 1, len(P))) if P[i]["id"] not in u["anchors"]]
        lat, cjk = tokens(u["text"])
        if en:
            cjk = set()   # 英文導讀對中文原文:只比數字與保留的英文專名
            lat = {t for t in lat if re.fullmatch(r"\d+(?:\.\d+)?%?", t) or t in cited}
        miss_l = {t for t in lat if t not in cited}; miss_c = {t for t in cjk if t not in cited}
        disp = {}
        for t in miss_l | miss_c:
            for nid in sorted(near_ids, key=lambda x: abs(idx[x] - min(ii))):
                if t in ntext[idx[nid]]: disp[t] = nid; break
        nums = {t for t in miss_l if re.fullmatch(r"\d+(?:\.\d+)?%?", t)}
        if nums: st.append("FAIL-NUMBER")
        d_lat = [t for t in disp if t in miss_l]; d_cjk = [t for t in disp if t in miss_c and t not in hi_freq]
        prose = view in ("ste_zh", "ste_en")   # 改寫型產物:CJK 位移只當預篩 WARN(ste_zh r1 實測 FAIL 精確度 1/8)
        if d_lat or (len(d_cjk) >= 2 and not prose): st.append("FAIL-DISPLACED")
        elif disp: st.append("WARN-DISPLACED")
        head_only = [t for t in (miss_l | miss_c) - set(disp) if t in heads and t not in hi_freq]
        if len(head_only) >= 2: st.append("WARN-HEADING" if prose else "FAIL-HEADING")
        if not en:
            ut = norm(u["text"])
            for h in HEDGES:
                if h in cited and h not in ut:
                    hits = [m.start() for t in (cjk - miss_c - hi_freq) for m in re.finditer(re.escape(t), cited)]
                    if any(abs(cited.find(h) - p) <= 12 for p in hits):
                        st.append(f"WARN-HEDGE-DROPPED:{h}"); break
            if any(c in ut for c in CAUSAL[:4]) and not any(c in cited for c in CAUSAL[:4]):
                st.append("WARN-CAUSAL-ADDED")
        else:
            lt = " " + u["text"].lower() + " "
            if any(c in lt for c in (" so ", "because", "therefore")) and not any(c in cited for c in ("所以", "因此", "因為")):
                st.append("WARN-CAUSAL-ADDED")
        st = st or ["PASS"]
        for s in st: counts[s.split(":")[0]] = counts.get(s.split(":")[0], 0) + 1
        res.append({**u, "status": st, "displaced_to": disp, "missing_numbers": sorted(nums)})
    (run / "verify").mkdir(exist_ok=True)
    (run / "verify" / f"provenance_{view}{'_' + Path(f).stem if f else ''}.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1))
    fails = [r for r in res if any(s.startswith("FAIL") for s in r["status"])]
    for r in fails[:25]:
        print(r["status"], r["id"], r["anchors"], r["text"][:40], r.get("displaced_to") or "", r.get("missing_numbers") or "")
    print(view, f"units={len(res)}", json.dumps(counts, ensure_ascii=False), "PASS" if not fails else f"{len(fails)} FAIL")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
