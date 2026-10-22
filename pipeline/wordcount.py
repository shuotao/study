#!/usr/bin/env python3
"""wordcount.py — the word-count QAQC chain of one session (study CLAUDE.md checklist 6, E1 + E4).

One table from the ORIGINAL transcript (all cues, E4) through every stage's frozen output, counted on one basis
(E1: Han characters for Chinese talks, words otherwise; whitespace and image syntax excluded; Phases 4-5 split into
the speaker's body text and the added `>` blocks). Each row is checked against its band:

  p1-clean   Phase A text  vs original          >= 0.90  (warn: drops are hallucination/garble, but see E4)
  p3-polish  cleaned.md    vs Phase A text      0.95-1.05 (fail; the study zero-omission band)
  p3-punct   cleaned.md    vs p3-polish         == 1.000 (fail; punctuation only)
  p3-hooks   cleaned.md    vs p3-punct          1.00-1.12 (fail; insert-only hooks)
  p4-terms   enhanced body vs final cleaned.md  == 1.000 (fail; supplements live in > blocks)
  p5-stance  notes body    vs its source body   == 1.000 (fail)
  end-to-end final body    vs original          reported (E4: retention traced from Step 1 to the last product)

  python3 pipeline/wordcount.py <slug>      → prints the table, writes sessions/<slug>/wordcount_report.json
Exit 1 when a fail band is broken. Used by `gsn.py wordcount`, `gsn.py audit` (A9) and the observer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import content_units, is_cjk_text, load_meta, session_dir, srt_text  # noqa: E402


def body(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))


def frozen(sdir: Path, stage: str, name: str) -> Path | None:
    p = sdir / ".gsn" / f"{stage}.out.{name}"
    if p.exists():
        return p
    return None


def chain(sdir: Path) -> tuple[list[dict], bool]:
    meta = load_meta(sdir)
    orig_txt = srt_text(sdir / "transcript.srt")
    cjk = is_cjk_text(orig_txt)
    n = lambda s: content_units(s, cjk)
    unit = "Han chars" if cjk else "words"
    rows, ok = [], True

    def add(stage, product, units, ref_name, ref_units, lo=None, hi=None, level="fail", extra=""):
        nonlocal ok
        ratio = round(units / ref_units, 3) if ref_units else None
        band_ok = None
        if lo is not None and ratio is not None:
            band_ok = lo <= ratio <= hi
            if not band_ok and level == "fail":
                ok = False
        rows.append({"stage": stage, "product": product, "units": units, "vs": ref_name, "ratio": ratio,
                     "band": None if lo is None else f"{lo:.2f}-{hi:.2f}", "ok": band_ok, "level": level,
                     "vs_original": round(units / u_orig, 3) if u_orig else None, "note": extra})

    u_orig = n(orig_txt)
    rows.append({"stage": "p1-transcribe", "product": "transcript.srt (all cues)", "units": u_orig, "vs": "—",
                 "ratio": None, "band": None, "ok": None, "level": "info", "vs_original": 1.0, "note": "E4 base"})
    if not (sdir / "cleaned.srt").exists():
        return rows, ok
    u_a = n(srt_text(sdir / "cleaned.srt"))
    add("p1-clean", "cleaned.srt", u_a, "original", u_orig, 0.90, 1.00, "warn")

    plan = meta.get("plan", [])
    if (sdir / "transcript.zh-TW.srt").exists():
        rows.append({"stage": "p2-translate", "product": "transcript.zh-TW.srt", "units": n(srt_text(sdir / "transcript.zh-TW.srt")),
                     "vs": "—", "ratio": None, "band": None, "ok": None, "level": "info", "vs_original": None,
                     "note": "cross-language: 1:1 cue alignment is the check (E3), not a char ratio"})

    prev = None
    for stage, ref_label, lo, hi in (("p3-polish", "Phase A text", 0.95, 1.05), ("p3-punct", "p3-polish", 1.0, 1.0),
                                     ("p3-hooks", "p3-punct", 1.0, 1.12)):
        if stage not in plan:
            continue
        f = frozen(sdir, stage, "cleaned.md")
        if not f:
            break
        u = n(f.read_text(encoding="utf-8"))
        add(stage, "cleaned.md", u, ref_label, u_a if stage == "p3-polish" else prev, lo, hi)
        prev = u
    final_md = sdir / "cleaned.md"
    u_final = n(final_md.read_text(encoding="utf-8")) if final_md.exists() else None

    for stage, name, src_name in (("p4-terms", "enhanced.md", "cleaned.md"),
                                  ("p5-stance", f"notes_{meta.get('identity', '')}.md",
                                   "enhanced.md" if "p4-terms" in plan else "cleaned.md")):
        f = frozen(sdir, stage, name) or (sdir / name if (sdir / name).exists() else None)
        if stage not in plan or not f:
            continue
        txt = f.read_text(encoding="utf-8")
        src = (sdir / src_name).read_text(encoding="utf-8")
        ub, ut = n(body(txt)), n(txt)
        add(stage, f"{name} (speaker body)", ub, f"{src_name} body", n(body(src)), 1.0, 1.0,
            extra=f"added in > blocks: {ut - ub} {unit} ({(ut - ub) / max(1, ub):.0%} of body)")

    if u_final is not None:
        add("end-to-end", "final cleaned.md", u_final, "original", u_orig, None, None, "info",
            extra="E4: retention traced from Step 1 to the last product (headings/hooks included)")
    for r in rows:
        r["unit"] = unit
    return rows, ok


def table(rows: list[dict]) -> str:
    out = ["| stage | product | units | vs | ratio | band | vs original | result | note |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        res = "" if r["ok"] is None else ("PASS" if r["ok"] else ("FAIL" if r["level"] == "fail" else "WARN"))
        out.append(f"| {r['stage']} | {r['product']} | {r['units']} {r.get('unit', '')} | {r['vs']} | "
                   f"{'' if r['ratio'] is None else r['ratio']} | {r['band'] or ''} | "
                   f"{'' if r['vs_original'] is None else r['vs_original']} | {res} | {r['note']} |")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sdir = session_dir(sys.argv[1])
    rows, ok = chain(sdir)
    print(table(rows))
    (sdir / "wordcount_report.json").write_text(json.dumps({"ok": ok, "rows": rows}, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    print(f"\nwordcount: {'PASS' if ok else 'FAIL'} → {sdir.name}/wordcount_report.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
