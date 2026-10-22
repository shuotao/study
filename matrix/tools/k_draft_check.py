#!/usr/bin/env python3
"""K.json 初稿閘門(機械)。用法: k_draft_check.py <run_dir>
D1 5–7 點且 k 依序 K1..Kn   D2 錨點都存在、每點 3–35 段   D3 point ≤ 45 漢字、非空
D4 錨點不全是聽眾段(有 speakers.json 時)   D5 重點之間錨點重疊 ≤ 50%
"""
import sys, json, re
from pathlib import Path
CJK = re.compile(r"[一-鿿]")
run = Path(sys.argv[1]); f = []
K = json.loads((run / "K.json").read_text(encoding="utf-8"))["K"]
ids = {p["id"] for p in json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))["paragraphs"]}
if not 5 <= len(K) <= 7: f.append(f"D1 {len(K)} points")
if [k["k"] for k in K] != [f"K{i + 1}" for i in range(len(K))]: f.append("D1 order")
spk = json.loads((run / "speakers.json").read_text(encoding="utf-8"))["paragraphs"] if (run / "speakers.json").exists() else {}
for k in K:
    a = k.get("anchors", [])
    if set(a) - ids: f.append(f"D2 {k['k']} unknown {sorted(set(a) - ids)}")
    if not 3 <= len(a) <= 35: f.append(f"D2 {k['k']} {len(a)} anchors")
    n = len(CJK.findall(k.get("point", "")))
    if not k.get("point") or n > 45: f.append(f"D3 {k['k']} point {n} CJK")
    if spk and all(spk.get(x, {}).get("who") == "audience" for x in a): f.append(f"D4 {k['k']} audience only")
for i, x in enumerate(K):
    for y in K[i + 1:]:
        s, t = set(x["anchors"]), set(y["anchors"])
        if s and t and len(s & t) / min(len(s), len(t)) > .5: f.append(f"D5 {x['k']}/{y['k']} overlap")
for x in f: print("FAIL", x)
print(f"K={len(K)}", "PASS" if not f else f"FAIL {len(f)}"); sys.exit(1 if f else 0)
