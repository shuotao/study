#!/usr/bin/env python3
"""IV 廣度關聯閘門。用法: links_check.py
L1 每個候選都被判過一次(links 或 excluded,不多不少)    L2 不得自創候選以外的關聯
L3 type ∈ 呼應/延伸/實例/對照/不同看法                    L4 why 必填、≤ 70 個漢字(硬上限;prompt 目標 ≤60);排除也要寫原因
L5 原因要具體:同一句 why 出現 > 3 次即紅燈(排除理由會公開,不能用一句通用說明打發)
L7 族譜:每個有 K.json 的場次 meta.json 都有 genealogy;候選與判斷只能在同一族譜內(不同族譜的場次不比對)
L6 近似重複:去掉場次代號與數字後,某句 why 與 ≥3 句其他 why 的字元二元組 Jaccard ≥ 0.75 → 紅燈(擋「換一個字」的通用句)
"""
import sys, json, re
from pathlib import Path
N = Path(__file__).resolve().parent.parent
TYPES = {"呼應", "延伸", "實例", "對照", "不同看法"}
CJK = re.compile(r"[一-鿿]")
try:
    C = json.loads((N / "links/candidates.json").read_text(encoding="utf-8"))
    L = json.loads((N / "links/links.json").read_text(encoding="utf-8"))
except (OSError, ValueError) as ex:
    print("FAIL L0 cannot read links/candidates.json or links/links.json:", ex); sys.exit(1)
key = lambda x: tuple(sorted((x["a"], x["b"])))
cand = {key(c) for c in C["candidates"]}; f = []
GEN = {r.name: json.loads((r / "meta.json").read_text(encoding="utf-8")).get("genealogy", "")
       for r in (N / "runs").iterdir() if (r / "K.json").exists() and (r / "meta.json").exists()}
f += [f"L7 {r} meta.json has no genealogy" for r, g in GEN.items() if not g]
g_of = lambda cid: GEN.get(cid.split("#")[0], "")
f += [f"L7 cross-genealogy pair: {key(x)}" for x in C["candidates"] + L["links"] + L["excluded"] if g_of(x["a"]) != g_of(x["b"])]
seen = {}
for x in L["links"] + L["excluded"]:
    k = key(x); seen[k] = seen.get(k, 0) + 1
    if k not in cand: f.append(f"L2 not a candidate: {k}")
    if not x.get("why") or len(CJK.findall(x["why"])) > 70: f.append(f"L4 why missing/too long: {k}")
for x in L["links"]:
    if x["type"] not in TYPES: f.append(f"L3 bad type {x['type']}: {key(x)}")
import collections
for w, n in collections.Counter(x["why"] for x in L["links"] + L["excluded"]).items():
    if n > 3: f.append(f"L5 same why x{n}: {w[:30]}")
import re as _re
def _bg(s):
    s = _re.sub(r"[A-Z]{2,}\d+|K\d+|\d+(?:\.\d+)?", "", s); return {s[i:i + 2] for i in range(len(s) - 1)}
W = [(x["why"], _bg(x["why"])) for x in L["links"] + L["excluded"]]
for i, (w, a) in enumerate(W):
    near = sum(1 for j, (_, b) in enumerate(W) if j != i and a and b and len(a & b) / len(a | b) >= .75)
    if near >= 3: f.append(f"L6 near-duplicate why x{near + 1}: {w[:30]}")
for k in cand:
    if seen.get(k, 0) != 1: f.append(f"L1 judged {seen.get(k, 0)}x: {k}")
for x in f[:20]: print("FAIL", x)
print(f"candidates={len(cand)} links={len(L['links'])} excluded={len(L['excluded'])}", "PASS" if not f else f"FAIL {len(f)}")
sys.exit(1 if f else 0)
