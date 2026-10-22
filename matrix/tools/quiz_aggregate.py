#!/usr/bin/env python3
"""象限 I 理解任務測驗彙整(取代「難句數」量法;TAO 依建議 2026-10-12)。
用法: quiz_aggregate.py <run_dir>
讀 quiz.json(題目+答案鍵)、verify/quiz_ans_t*.json(persona 作答)、verify/quiz_grades.json(grader 對理解題的判定)。
導覽題:答案中的 href(ii.html#pNNNN)須屬於該題 acceptable targets → 機械判定,不交 LLM。
gate:理解題答對數中位數 ≥2/3、導覽題 ≥2/3 次成功。興趣只當參考指標(interest_ok),不擋。
"""
import sys, re, json, glob, statistics
from pathlib import Path

run = Path(sys.argv[1]); Q = json.loads((run / "quiz.json").read_text(encoding="utf-8"))["items"]
nav = [q for q in Q if q["id"].startswith(("n", "nav"))]; comp = [q for q in Q if q not in nav]
G = json.loads((run / "verify/quiz_grades.json").read_text(encoding="utf-8"))   # {"t1":{"q1":true,...},...}
rows = []
for f in sorted(glob.glob(str(run / "verify/quiz_ans_t*.json"))):
    t = Path(f).stem.split("_")[-1]; a = json.loads(Path(f).read_text(encoding="utf-8"))
    correct = sum(1 for q in comp if G.get(t, {}).get(q["id"]) is True)
    nav_ok = []
    for q in nav:
        acc = set(re.findall(r"p\d{4}", " ".join(q.get("acceptable_targets") or [])))   # 只認 acceptable_targets(不掃整題 JSON,避免 key 裡的編號被誤算)
        got = set(re.findall(r"p\d{4}", a["answers"].get(q["id"], "")))
        nav_ok.append(bool(got & acc))
    rows.append({"trial": t, "comp_correct": correct, "comp_total": len(comp), "nav_ok": all(nav_ok), "interest": a.get("interest"), "neutrality": a.get("neutrality")})
med = lambda k: statistics.median([r[k] for r in rows if r.get(k) is not None]) if any(r.get(k) is not None for r in rows) else None
res = {"n": len(rows), "runs": rows, "median_comp": med("comp_correct"), "nav_success": sum(r["nav_ok"] for r in rows),
       "median_interest": med("interest"), "median_neutrality": med("neutrality")}
res["pass"] = len(rows) >= 3 and res["median_comp"] >= 2 and res["nav_success"] >= 2
res["interest_ok"] = (res["median_interest"] or 0) >= 4   # 參考指標:兩場皆因原文缺時程/經費/第一步而偏低,補不出來,不設為門檻
(run / "verify/quiz_aggregate.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
for r in rows: print(r)
print({k: v for k, v in res.items() if k != "runs"}); sys.exit(0 if res["pass"] else 1)
