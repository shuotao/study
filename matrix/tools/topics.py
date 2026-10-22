#!/usr/bin/env python3
"""III 深挖題目(確定性轉換):把「講者講到但沒講完」的地方整理成 topics.json。
用法: topics.py <run_dir>
來源(依序):iv.json 的 questions + 缺項(新版)→ 舊版 iv.html 的 data-check 項目。
題目只是「起點」;讀者也可以在 III 自己反白任何一句開題。
topics.json = [{"k","kind","text","quote"(選),"refs":[pNNNN]}]
"""
import sys, json, re, html
from pathlib import Path

KIND = {"unsupported": "沒給依據", "hedged": "講者保留語氣", "relayed": "轉述他人", "unclear": "錄音不清",
        "absent": "原文未提", "ext": "需外部核對", "gaps": "原文未提", "deep": "值得深挖"}


def main():
    run = Path(sys.argv[1]); out = []
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    if (run / "iv.json").exists():
        D = json.loads((run / "iv.json").read_text(encoding="utf-8"))
        for it in D["items"]:
            for q in it.get("questions", []):
                out.append({"k": it["k"], "kind": q["kind"], "text": q["text"], "refs": q.get("refs", [])})
            miss = [g for g in meta.get("expert_checklist", []) if it.get("gaps", {}).get(g) != "有"]
            if miss:
                out.append({"k": it["k"], "kind": "gaps", "text": "這一點沒有提到：" + "、".join(miss), "refs": it["claim"]["refs"]})
    elif (run / "topics.json").exists():
        print("topics.json 已存在且無 iv.json:保留(舊版 IV 已轉換)"); return
    elif (run / "iv.html").exists():
        t = (run / "iv.html").read_text(encoding="utf-8")
        for sec in re.finditer(r'<section[^>]*data-k="(K\d+)".*?</section>', t, re.S):
            for m in re.finditer(r'<li data-check="([a-z]+)" data-anchors="([^"]*)"><q>(.*?)</q>(.*?)</li>', sec.group(0), re.S):
                kind, anc, quote, rest = m.groups()
                why = html.unescape(re.sub(r"<[^>]+>", "", rest)).strip()
                why = re.sub(r"^[a-z]+：", "", why).strip()
                out.append({"k": sec.group(1), "kind": kind, "quote": html.unescape(quote), "text": why, "refs": anc.split()})
    if (run / "topics.json").exists():   # 保留 K 的深度提示(kind=deep,原 iv_angle,2026-10-13 移入)
        out += [x for x in json.loads((run / "topics.json").read_text(encoding="utf-8")) if x.get("kind") == "deep"]
        out.sort(key=lambda x: int(x["k"][1:]))
    (run / "topics.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("topics", len(out))


if __name__ == "__main__":
    main()
