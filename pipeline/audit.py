#!/usr/bin/env python3
"""audit.py — after-the-fact proof that a session was produced by the rules, not by shortcuts.

Never trusts what an agent said; reads the ledger, the snapshots and the files.

  A0 ledger hash chain intact (no entry inserted, removed, reordered or edited)
  A1 transcript.srt unchanged since Phase 1 (immutability)
  A2 every planned stage is accounted for: done/tool entry, or still pending with its marker
     (a stage with no marker and no done entry = marker deleted by hand)
  A3 stages finished in plan order, each judgment stage opened before it was done
  A4 base snapshots unchanged since the stage opened
  A5 chain continuity: each stage's input snapshot == the previous stage's approved output
     (nothing edited between stages)
  A6 live files == last approved output (nothing edited after done)
  A7 every judgment stage re-gated NOW on its frozen output snapshot
  A8 repair rounds per stage <= 3 (circuit break respected)
  A9 word-count chain: original cues → every frozen stage output in its band (pipeline/wordcount.py)

Writes sessions/<slug>/audit_report.json. Exit 1 on any failure.
Usage: python3 pipeline/audit.py <slug>
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import gates  # noqa: E402
from pipeline.common import (STAGE_BY_ID, STAGE_ORDER, load_meta, marker_path, read_ledger,  # noqa: E402
                             session_dir, sha1_file, verify_chain)


def regate_frozen(sdir: Path, stage: str, outputs: dict) -> list[dict]:
    """Rebuild a throwaway copy of the session with the stage's frozen output and run its gate."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / sdir.name
        shutil.copytree(sdir, tmp, symlinks=True, ignore=shutil.ignore_patterns("source.*", ".groq_chunks"))
        for f in outputs:
            frozen = sdir / ".gsn" / f"{stage}.out.{f}"
            if frozen.exists():
                shutil.copyfile(frozen, tmp / f)
        if stage == "p6-matrix":
            return gates.run_gate(stage, sdir)        # matrix runs live outside the session
        if stage == "p2-translate":
            return gates.run_gate(stage, tmp)
        return gates.run_gate(stage, tmp)


def audit(sdir: Path) -> tuple[list[dict], dict]:
    meta = load_meta(sdir)
    plan = meta.get("plan", [])
    L = read_ledger(sdir)
    rows = []

    def row(rid, ok, detail="", level="fail"):
        rows.append({"id": rid, "ok": bool(ok), "detail": detail, "level": level})

    errs = verify_chain(L)
    row("A0 ledger hash chain", not errs, "; ".join(errs[:5]))

    t0 = next((e for e in L if e["action"] == "tool" and e["stage"] == "p1-transcribe"), None)
    row("A1 transcript.srt immutable", t0 and t0["outputs"].get("transcript.srt") == sha1_file(sdir / "transcript.srt"),
        "" if t0 else "no Phase 1 entry")

    finished = {e["stage"]: e for e in L if e["action"] in ("tool", "done")}
    opened = {e["stage"]: e for e in L if e["action"] == "open"}
    for st in plan:
        has_marker = marker_path(sdir, st).exists()
        ok = st in finished or has_marker
        row(f"A2 {st} accounted for", ok, "pending" if has_marker else ("" if ok else "no marker and no done entry: marker removed by hand?"))
        if STAGE_BY_ID[st]["kind"] == "judgment" and st in finished:
            row(f"A3 {st} opened before done", st in opened and opened[st]["seq"] < finished[st]["seq"])
            if finished[st].get("action") != "done":
                row(f"A3 {st} finished via `gsn.py done`", False)

    seqs = [finished[s]["seq"] for s in STAGE_ORDER if s in plan and s in finished]
    row("A3 stages finished in plan order", seqs == sorted(seqs), str(seqs))

    for st, e in opened.items():
        base = sdir / ".gsn" / f"{st}.base"
        row(f"A4 {st} base snapshot unchanged", sha1_file(base) == e.get("base_sha1"))

    # A5 continuity of cleaned.md through p3-polish → p3-punct → p3-hooks → (p4/p5/p6 read it)
    last_md = None
    for st in [s for s in STAGE_ORDER if s in plan and s in finished]:
        e = finished[st]
        if st in ("p3-punct", "p3-hooks", "p4-terms", "p6-matrix") and last_md and st in opened:
            row(f"A5 {st} input == previous approved cleaned.md", opened[st]["base_sha1"] == last_md)
        if "cleaned.md" in e.get("outputs", {}):
            last_md = e["outputs"]["cleaned.md"]

    latest = {}
    for e in L:
        if e["action"] in ("tool", "done"):
            for f, h in e.get("outputs", {}).items():
                latest[f] = h
    for f, h in latest.items():
        live = sha1_file((sdir.parent.parent / f) if f.startswith("matrix/") else sdir / f)
        row(f"A6 {f} unchanged since approved", live == h, "" if live == h else "edited after its gate passed")

    for st in plan:
        if STAGE_BY_ID[st]["kind"] == "judgment" and st in finished:
            res = regate_frozen(sdir, st, finished[st].get("outputs", {}))
            bad = [r["name"] for r in res if r["level"] == "fail" and not r["ok"]]
            row(f"A7 {st} gate re-run on frozen output", not bad, "; ".join(bad))

    from pipeline.wordcount import chain
    wc_rows, wc_ok = chain(sdir)
    broken = [f"{r['stage']} {r['ratio']} not in {r['band']}" for r in wc_rows if r["ok"] is False and r["level"] == "fail"]
    row("A9 word-count chain (original → every stage, same basis)", wc_ok, "; ".join(broken))
    final = next((r for r in wc_rows if r["stage"] == "end-to-end"), None)
    if final:
        row("A9 end-to-end retention vs ALL original cues (E4)", (final["ratio"] or 0) >= 0.95,
            f"{final['units']}/{wc_rows[0]['units']} = {final['ratio']}", "warn")

    rounds = {}
    for e in L:
        if e["action"] in ("gate-fail", "check-fail"):
            rounds[e["stage"]] = rounds.get(e["stage"], 0) + 1
    for st, n in rounds.items():
        row(f"A8 {st} repair rounds", n <= 3, f"{n} failed round(s)", "warn" if n <= 3 else "fail")

    timeline = [{"seq": e["seq"], "ts": e["ts"], "action": e["action"], "stage": e["stage"], "actor": e.get("actor")} for e in L]
    return rows, {"rounds": rounds, "timeline": timeline}


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sdir = session_dir(sys.argv[1])
    rows, extra = audit(sdir)
    for r in rows:
        mark = "PASS" if r["ok"] else ("FAIL" if r["level"] == "fail" else "WARN")
        print(f"{mark:4} {r['id']}" + (f" — {r['detail']}" if r["detail"] else ""))
    bad = [r for r in rows if r["level"] == "fail" and not r["ok"]]
    head = read_ledger(sdir)[-1]["hash"] if read_ledger(sdir) else None
    (sdir / "audit_report.json").write_text(json.dumps({"ok": not bad, "ledger_head": head, "rows": rows, **extra}, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(f"audit: {len(rows) - len(bad)}/{len(rows)} green → {sdir.name}/audit_report.json")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
