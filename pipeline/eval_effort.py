#!/usr/bin/env python3
"""eval_effort.py — measure which model × effort is good enough for each judgment stage.

Runs the Phase 3 chain (p3-polish → p3-punct → p3-hooks) on a fixture once per config, through the real
headless loop (fresh process per stage, gates re-run by the orchestrator, 3-round circuit breaker), and
records what the ledger proves: rounds per stage, wall time, pass/circuit-break, audit result and the gate
metrics (content ratio, 4-gram retention, paragraph median, hook growth). Configs run sequentially.

  python3 pipeline/eval_effort.py run --cli claude --configs sonnet:low sonnet:medium opus:medium haiku:medium
  python3 pipeline/eval_effort.py report          # → docs/qaqc/eval-effort.md from docs/qaqc/eval-effort.json

A blind quality read of the outputs (which version reads best, which one lost content) is a separate,
judgment step: give the judge `sessions/eval-*/cleaned.md` with the config names hidden.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import CJK_RE, REPO, SESSIONS, content_units, read_ledger  # noqa: E402
from pipeline.gates import ngram_retention  # noqa: E402

OUT_JSON = REPO / "docs/qaqc/eval-effort.json"
OUT_MD = REPO / "docs/qaqc/eval-effort.md"
STAGES = ["p3-polish", "p3-punct", "p3-hooks"]


def metrics(sdir: Path) -> dict:
    base = (sdir / ".gsn/p3-polish.base").read_text(encoding="utf-8")
    md = sdir / "cleaned.md"
    if not md.exists():
        return {}
    out = md.read_text(encoding="utf-8")
    polish = sdir / ".gsn/p3-polish.out.cleaned.md"
    punct = sdir / ".gsn/p3-punct.out.cleaned.md"
    paras = [p for p in re.split(r"\n\s*\n", out) if p.strip() and not p.strip().startswith("#")]
    lens = [len(CJK_RE.findall(p)) for p in paras]
    m = {"ratio": round(content_units(out) / max(1, content_units(base)), 3),
         "retention_4gram": round(ngram_retention(base, out), 3),
         "paragraphs": len(lens), "para_median": statistics.median(lens) if lens else 0,
         "headings": len(re.findall(r"^#{2,3} ", out, flags=re.M)),
         "colons": out.count("："), "quotes": out.count("「")}
    if polish.exists() and punct.exists():
        m["hook_growth"] = round(content_units(out) / max(1, content_units(punct.read_text(encoding="utf-8"))), 3)
    return m


def run_config(fixture: Path, ctx: Path, cli: str, model: str, effort: str) -> dict:
    stamp = dt.datetime.now().strftime("%m%d%H%M%S")
    slug = f"eval-{cli}-{model}-{effort}-{stamp}"
    r = subprocess.run([sys.executable, REPO / "gsn.py", "new", "--from-srt", fixture, "--slug", slug,
                        "--context", ctx, "--stop-at", "p3"], cwd=REPO, capture_output=True, text=True)
    if r.returncode:
        return {"config": f"{cli}:{model}:{effort}", "error": r.stderr[-400:]}
    t0 = dt.datetime.now()
    h = subprocess.run([sys.executable, REPO / "pipeline/headless.py", slug, "--cli", cli, "--model", model,
                        "--effort", effort, "--until", "p3-hooks"], cwd=REPO, capture_output=True, text=True)
    secs = (dt.datetime.now() - t0).total_seconds()
    sdir = SESSIONS / slug
    L = read_ledger(sdir)
    per = {}
    for st in STAGES:
        hl = [e for e in L if e["action"] == "headless" and e["stage"] == st]
        per[st] = {"rounds": len(hl), "gate_fails": sum(1 for e in L if e["action"] == "gate-fail" and e["stage"] == st),
                   "done": any(e["action"] == "done" and e["stage"] == st for e in L),
                   "seconds": sum(e.get("seconds", 0) for e in hl)}
    audit = subprocess.run([sys.executable, REPO / "gsn.py", "audit", slug], cwd=REPO, capture_output=True, text=True)
    return {"config": f"{cli}:{model}:{effort}", "slug": slug, "exit": h.returncode, "seconds": round(secs),
            "stages": per, "circuit_break": any(e["action"] == "circuit-break" for e in L),
            "audit_green": audit.returncode == 0, "metrics": metrics(sdir), "fixture": str(fixture.relative_to(REPO))}


def report() -> None:
    data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    rows = ["| config | p3 done | rounds polish/punct/hooks | gate fails | minutes | audit | ratio | 4-gram | para median | hook growth | colons |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in data["runs"]:
        if "error" in d:
            rows.append(f"| {d['config']} | error | | | | | | | | | |"); continue
        s, m = d["stages"], d.get("metrics", {})
        done = all(s[x]["done"] for x in STAGES)
        rows.append(f"| {d['config']} | {'yes' if done else 'NO'} | {'/'.join(str(s[x]['rounds']) for x in STAGES)} | "
                    f"{sum(s[x]['gate_fails'] for x in STAGES)} | {d['seconds'] / 60:.1f} | {'green' if d['audit_green'] else 'RED'} | "
                    f"{m.get('ratio', '')} | {m.get('retention_4gram', '')} | {m.get('para_median', '')} | {m.get('hook_growth', '')} | {m.get('colons', '')} |")
    head = OUT_MD.read_text(encoding="utf-8").split("<!-- table -->")[0] if OUT_MD.exists() else "# Effort eval\n\n"
    tail = OUT_MD.read_text(encoding="utf-8").split("<!-- /table -->")[1] if OUT_MD.exists() and "<!-- /table -->" in OUT_MD.read_text(encoding="utf-8") else "\n"
    OUT_MD.write_text(head + "<!-- table -->\n" + "\n".join(rows) + "\n<!-- /table -->" + tail, encoding="utf-8")
    print("\n".join(rows))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--cli", default="claude")
    r.add_argument("--configs", nargs="+", required=True, help="model:effort pairs")
    r.add_argument("--fixture", default="examples/talk-context/excerpt.srt")
    r.add_argument("--context", default="examples/talk-context/context.txt")
    sub.add_parser("report")
    a = ap.parse_args()
    if a.cmd == "report":
        report(); return 0
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {"runs": []}
    for cfg in a.configs:
        model, effort = cfg.split(":")
        print(f"[eval] {a.cli}:{model}:{effort} …", flush=True)
        res = run_config(REPO / a.fixture, REPO / a.context, a.cli, model, effort)
        data["runs"].append(res)
        OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")   # resumable record
        print(f"[eval]   → {json.dumps({k: res.get(k) for k in ('exit', 'seconds', 'audit_green', 'circuit_break')})}", flush=True)
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
