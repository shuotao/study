#!/usr/bin/env python3
"""iv.json gate — iv.json is the source of III deep-dive topics (tools/topics.py), not a page. Usage: iv_check.py <run_dir>
J1 K 順序 = K.json;每卡有 headline/claim/questions
J2 錨點:speaker 項 ⊆ 該 K 錨點;aux 項只用 hNNN 且存在;引用 speakers.json 聽眾段落的項必須 src=audience
J3 quotes 是錨點段落(或講義條目)的連續子字串
J4 gaps 鍵 = meta.expert_checklist,值 ∈ {有, 原文未提}
J5 每卡證據+追問合計 ≤ 12 條、主張 ≤ 120 字(可讀性;避免又碎掉)
J6 lead 不得點名 K(哪些值得細讀由工具判定,LLM 寫在 lead 會跟分級打架)
"""
import sys, json, re
from pathlib import Path

run = Path(sys.argv[1]); f = []
J = json.loads((run / "iv.json").read_text(encoding="utf-8"))
K = json.loads((run / "K.json").read_text(encoding="utf-8"))["K"]; kan = {k["k"]: set(k["anchors"]) for k in K}
P = {p["id"]: re.sub(r"\*\*(.+?)\*\*", r"\1", p["text"]) for p in json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))["paragraphs"]}
AUX = {i["id"]: i["text"] for i in json.loads((run / "aux.anchors.json").read_text(encoding="utf-8"))["items"]} if (run / "aux.anchors.json").exists() else {}
spk = json.loads((run / "speakers.json").read_text(encoding="utf-8"))["paragraphs"] if (run / "speakers.json").exists() else {}
aud_only = {p for p, v in spk.items() if v.get("who") == "audience"}
meta = json.loads((run / "meta.json").read_text(encoding="utf-8")); cl = meta.get("expert_checklist", [])
CJK = re.compile(r"[一-鿿]")
if [i["k"] for i in J["items"]] != [k["k"] for k in K]: f.append("J1 K order")
for it in J["items"]:
    k = it["k"]
    for fld in ("headline", "claim", "questions"):
        if not it.get(fld): f.append(f"J1 {k} missing {fld}")
    units = [("claim", {"refs": it["claim"].get("refs", []), "src": "speaker"})] + [("evidence", x) for x in it.get("evidence", [])] + [("questions", x) for x in it.get("questions", [])]
    for fld, x in units:
        refs = x.get("refs", []); src = x.get("src", "speaker")
        if fld != "questions" and not refs: f.append(f"J2 {k} {fld} item without refs: {x.get('text','')[:20]}")
        for r in refs:
            if r.startswith("h"):
                if r not in AUX: f.append(f"J2 {k} unknown aux {r}")
                if src != "aux" and fld != "questions": f.append(f"J2 {k} {fld} cites handout {r} but src!=aux")
            elif r not in kan[k]: f.append(f"J2 {k} {fld} ref {r} not in K anchors")
        if refs and set(refs) <= aud_only and src != "audience": f.append(f"J2 {k} {fld} cites only audience paragraphs {refs} but src!=audience")
    for q in it.get("quotes", []):
        pool = AUX.get(q["ref"], "") if q["ref"].startswith("h") else P.get(q["ref"], "")
        if q["q"] not in pool: f.append(f"J3 {k} quote not substring of {q['ref']}: {q['q'][:20]}")
    g = it.get("gaps", {})
    if cl and sorted(g) != sorted(cl): f.append(f"J4 {k} gaps keys {sorted(g)}")
    if any(v not in ("有", "原文未提") for v in g.values()): f.append(f"J4 {k} gaps values")
    n = len(it.get("evidence", [])) + len(it.get("questions", []))
    if n > 12: f.append(f"J5 {k} {n} evidence+question items > 12 (too fragmented)")
    if len(CJK.findall(it["claim"]["text"])) > 120: f.append(f"J5 {k} claim > 120 CJK")
if re.search(r"(?<![A-Za-z0-9])K\d+(?!\d)", J.get("lead", "")): f.append("J6 lead mentions K ids (tiering is mechanical; do not restate it)")
for x in f[:30]: print("FAIL", x)
print(f"items={len(J['items'])}", "PASS" if not f else f"{len(f)} failure(s)"); sys.exit(1 if f else 0)
