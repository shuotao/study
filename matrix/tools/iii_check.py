#!/usr/bin/env python3
"""iii.html 驗收(§V5 / §AC trace)。用法: iii_check.py <run_dir>
T1 逐字 byte-equal(去標籤、去 ** 後)  T2 h2/h3 數與順序  T3 圖片數、路徑存在、位置
T4 claims 子字串/數量/類型  T5 無孤兒 <p>  T6 無外部資源
"""
import sys, re, json, html
from pathlib import Path

CJK = re.compile(r"[一-鿿]")


def main():
    run = Path(sys.argv[1]).resolve()
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    src = Path(A["source"]).read_text(encoding="utf-8").splitlines()
    t = (run / "iii.html").read_text(encoding="utf-8")
    main_html = t.split("<aside", 1)[0]
    f = []
    # T1
    for p in A["paragraphs"]:
        m = re.search(rf'<p id="{p["id"]}"[^>]*><a class="pid"[^>]*>{p["id"]}</a>(.*?)</p>', t, re.S)
        got = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r'<span class="aud-tag">聽眾</span>', "", m.group(1)))) if m else None
        if got != re.sub(r"\*\*(.+?)\*\*", r"\1", p["text"]):
            f.append(f"T1 {p['id']}")
    if len(re.findall(r'<p id="p\d{4}"', t)) != len(A["paragraphs"]):
        f.append("T1 paragraph count")
    # T2
    h2 = [html.unescape(x) for x in re.findall(r"<h2 id=\"s\d+\">(.*?)</h2>", t)]
    h3 = [html.unescape(x) for x in re.findall(r"<h3>(.*?)</h3>", t)]
    s_h2 = [l[3:].strip() for l in src if l.startswith("## ")]
    s_h3 = [l[4:].strip() for l in src if l.startswith("### ")]
    if h2 != s_h2: f.append(f"T2 h2 {len(h2)} vs {len(s_h2)}")
    if h3 != s_h3: f.append(f"T2 h3 {len(h3)} vs {len(s_h3)}")
    # T3
    imgs = re.findall(r'<figure data-(after|before)="(p\d{4})"><img[^>]*src="([^"]+)"', t)
    s_imgs = [m.group(1) for l in src if (m := re.match(r"^!\[.*?\]\((.*?)\)\s*$", l))]
    body_imgs = s_imgs
    if len(imgs) != len(body_imgs):
        f.append(f"T3 images {len(imgs)} vs {len(body_imgs)}")
    for _, pid, path in imgs:
        if not (run / html.unescape(path)).resolve().exists():
            f.append(f"T3 missing {path}")
    # T4
    ids = {p["id"]: p["text"] for p in A["paragraphs"]}
    claims = json.loads((run / "claims.json").read_text(encoding="utf-8")) if (run / "claims.json").exists() else []
    per_sec, nums = {}, 0
    for c in claims:
        if c["type"] not in ("主張", "條件", "例外", "步驟", "數字"):
            f.append(f"T4 type {c['type']}")
        if len(CJK.findall(c["claim"])) < 8:
            f.append(f"T4 short {c['claim'][:20]}")
        plain = lambda s: re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        if not any(c["claim"] in ids.get(a, "") or c["claim"] in plain(ids.get(a, "")) for a in c["anchors"]):
            f.append(f"T4 not-substring {c['anchors']} {c['claim'][:24]}")
        for a in c["anchors"]:
            if a in ids:
                sec = next(p["section"] for p in A["paragraphs"] if p["id"] == a)
                per_sec[sec] = per_sec.get(sec, 0) + 1
        nums += c["type"] == "數字"
    npar = len(A["paragraphs"]); cmin = max(20, round(npar * 0.3)); nmin = max(4, round(npar * 0.06))   # 依段落數縮放(BES1245:132 段 → 40/8)
    spk = json.loads((run / "speakers.json").read_text(encoding="utf-8"))["paragraphs"] if (run / "speakers.json").exists() else {}
    for c in claims:   # T7 講者歸屬:引文落在聽眾發言內的主張必須標 speaker=audience(反之亦然)
        aud = False
        for a in c["anchors"]:
            info = spk.get(a, {})
            if info.get("who") == "audience" or any(c["claim"] in sp or sp in c["claim"] for sp in info.get("audience_spans", []) + info.get("candidate_audience_spans", [])):
                aud = True
        if aud and c.get("speaker") != "audience": f.append(f"T7 {c.get('cid')} quotes audience speech but speaker!=audience")
        if not aud and c.get("speaker") == "audience": f.append(f"T7 {c.get('cid')} marked audience but quote is the speaker's")
    if (run / "claims.json").exists():   # 主張清單是可選的:沒有時 III 只提供原文+註記+深挖題目(SPEC §2: III only for deep-study runs)
        if len(claims) < cmin: f.append(f"T4 count {len(claims)}<{cmin}")
        low = [s for s in A["sections"] if per_sec.get(s, 0) < 2]
        if low: f.append(f"T4 sections<2 {low}")
        if nums < nmin: f.append(f"T4 number {nums}<{nmin}")
    # T5
    orphans = [x for x in re.findall(r"<p(?![^>]*\bid=\"p\d{4}\")[^>]*>", main_html)]
    if orphans: f.append(f"T5 orphan <p> x{len(orphans)}")
    # T6
    if re.search(r'<script[^>]+src=|<link[^>]+href="http', t): f.append("T6 external resource")
    print(f"paras={len(A['paragraphs'])} h2={len(h2)} h3={len(h3)} imgs={len(imgs)} claims={len(claims)} number={nums}")
    for x in f[:40]: print("FAIL", x)
    print("PASS" if not f else f"{len(f)} failure(s)")
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
