#!/usr/bin/env python3
"""Batch I/O for the link judgment step (AI-facing).
Usage:
  links_merge.py batches [--n 4]   write links/batch_<i>.json for candidates not yet judged (skips Jev auto-excluded)
  links_merge.py merge             merge links/judged_*.json into links/links.json, then run links_check
Batch item = {a, b, shared, A:{session, point, excerpt}, B:{...}}; judges follow prompts/worker_links.md.
"""
import sys, json, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from eval_links import key

N = Path(__file__).resolve().parent.parent; LJ = N / "links/links.json"


def load():
    return json.loads(LJ.read_text(encoding="utf-8")) if LJ.exists() else {"judged_by": "", "links": [], "excluded": []}


def batches(n):
    D = json.loads((N / "links/candidates.json").read_text(encoding="utf-8")); C = {c["id"]: c for c in D["cards"]}; L = load()
    done = {key(x["a"], x["b"]) for x in L["links"] + L["excluded"]}
    jj = N / "links/judged_jev.json"
    if jj.exists(): done |= {key(x["a"], x["b"]) for x in json.loads(jj.read_text(encoding="utf-8"))["excluded"]}
    cache = {}

    def excerpt(cid):
        run, k = cid.split("#")
        if run not in cache:
            cache[run] = ({p["id"]: p["text"] for p in json.loads((N / "runs" / run / "source.anchors.json").read_text(encoding="utf-8"))["paragraphs"]},
                          {x["k"]: x for x in json.loads((N / "runs" / run / "K.json").read_text(encoding="utf-8"))["K"]})
        P, K = cache[run]; return " / ".join(P[a][:120] for a in K[k]["anchors"][:4])
    todo = [c for c in D["candidates"] if key(c["a"], c["b"]) not in done]
    for i in range(n):
        B = [{"a": c["a"], "b": c["b"], "shared": c["shared"],
              "A": {"session": C[c["a"]]["title"], "point": C[c["a"]]["point"], "excerpt": excerpt(c["a"])},
              "B": {"session": C[c["b"]]["title"], "point": C[c["b"]]["point"], "excerpt": excerpt(c["b"])}} for c in todo[i::n]]
        if B: (N / f"links/batch_{i + 1}.json").write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"to judge: {len(todo)} in {min(n, len(todo))} batches")


def merge():
    L = load(); have = {key(x["a"], x["b"]) for x in L["links"] + L["excluded"]}; added = 0
    for f in sorted((N / "links").glob("judged_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for x in d.get("links", []):
            if key(x["a"], x["b"]) not in have: L["links"].append({k: x[k] for k in ("a", "b", "type", "why")}); have.add(key(x["a"], x["b"])); added += 1
        for x in d.get("excluded", []):
            if key(x["a"], x["b"]) not in have: L["excluded"].append({k: x[k] for k in ("a", "b", "why")}); have.add(key(x["a"], x["b"])); added += 1
    LJ.write_text(json.dumps(L, ensure_ascii=False, indent=1), encoding="utf-8"); print("merged", added)
    sys.exit(subprocess.run([sys.executable, str(N / "tools/links_check.py")]).returncode)


if __name__ == "__main__":
    batches(int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4) if sys.argv[1] == "batches" else merge()
