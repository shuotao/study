#!/usr/bin/env python3
"""gsn.py — Good-Student Notes pipeline (Phase 1-6), the single entry point.

  python3 gsn.py doctor                          check / set up the environment (also run by /init)
  python3 gsn.py new <media> [options]           create sessions/<slug>/ and run the deterministic stages
  python3 gsn.py new --from-srt <file.srt> ...   start from an existing SRT (no Groq call)
  python3 gsn.py status <slug>                   stage table + the next step
  python3 gsn.py next <slug>                     print the task card of the next pending judgment stage
  python3 gsn.py check <slug> [stage]            run gates, change nothing
  python3 gsn.py done <slug> <stage> [--actor A] run the stage gate; only if green: clear marker, log, open next stage
  python3 gsn.py audit <slug>                    re-run every gate + verify the ledger (shortcut detection)
  python3 gsn.py wordcount <slug>                word-count QAQC chain: original cues → every stage (E1 / E4 / 95-105%)
  python3 gsn.py improve [--session S]           open items of the improvement loop (study pipeline_logger queue)
  python3 gsn.py headless <slug> --cli claude|gemini|codex|copilot|agy [--model M] [--effort E] [--until STAGE]
                                                 drive pending stages through a headless agent CLI (OAuth login, no API key)

new options:
  --context TEXT|FILE   speaker names, companies, products, key terms (Groq prompt + Phase 3 name checks)
  --lang zh|en          transcription language (zh: study groq_transcribe.py · en: groq_transcribe_en.py)
  --no-prompt           send no prompt to Groq (noisy rooms: prevents prompt-echo hallucination)
  --chunk-seconds N     chunk length (default 600; 300 for noisy rooms)
  --domain NAME         typo dictionary overlay dict/typo_dict.<NAME>.json
  --s2t                 convert Simplified-drift glyphs to Taiwan Traditional in cleaned.srt
  --phase-a upgrade|upstream  Phase A cleaner: pipeline/phase_a_clean.py (default, won the comparison) or SRT/qaqc_srt.py
  --translate zh-TW     Phase 2: zh-TW subtitle track for a foreign-language talk (study srt_zhtw.py)
  --terms               Phase 4: term supplements → enhanced.md
  --identity ROLE       Phase 5: stance notes → notes_<ROLE>.md
  --matrix              Phase 6: Good-Student Matrix
  --stop-at p1..p6      last phase to run (default: p3; p4-p6 also run when their option is given)

Deterministic stages call the field-proven study tools unchanged (docs/upstream.sha1).
Judgment stages are never executed by this script: it writes a marker (.<stage>.pending.json), the agent
does the work, and `gsn.py done` lets the marker go only when the stage gate is green. Rules: CLAUDE.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from pipeline.common import (SESSIONS, STAGE_BY_ID, STAGE_ORDER, STAGES, STOP_AT, append_ledger,  # noqa: E402
                             load_meta, marker_path, pending_markers, read_ledger, rel, save_meta,
                             session_dir, sha1_file, srt_text)
from pipeline import gates  # noqa: E402

PY = sys.executable
GROQ = {"zh": REPO / ".claude/skills/good-student-notes/scripts/groq_transcribe.py",
        "en": REPO / "scripts/lang/en/groq_transcribe_en.py"}
QAQC_SRT = REPO / "SRT/qaqc_srt.py"
SRT_ZHTW = REPO / "scripts/lang/en/srt_zhtw.py"
S2T = REPO / "scripts/s2t_normalize.py"
MEDIA_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus", ".mp4", ".mov", ".mkv", ".webm", ".m4v"}


# ─── study log → check → improve loop (scripts/pipeline_logger.py, unchanged) ───

def loop_log(sdir: Path, stage: str, tool: str, res: list[dict]) -> None:
    """Every gate result goes to the study loop: one log line per stage; each failed gate opens an improvement
    item; a later green run of the same stage closes that session's open items for it (the consumer study lacked)."""
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import pipeline_logger as pl
        failed = [r for r in res if not r["ok"] and r["level"] == "fail"]
        warned = [r for r in res if not r["ok"] and r["level"] == "warn"]
        status = "fail" if failed else ("warn" if warned else "pass")
        pl.log_stage(sdir, stage, tool, status, metrics={"gates": len(res), "failed": len(failed)},
                     detail="; ".join(f"{r['name']}: {r['detail']}" for r in failed + warned)[:500])
        if failed:
            for r in failed:
                pl.enqueue_improvement(stage, sdir.name, f"{r['name']} — {r['detail']}"[:400],
                                       f"see {STAGE_BY_ID[stage].get('prompt', 'prompts/rules.md')}")
        else:
            pl.close_improvement(lambda rec: rec.get("session") == sdir.name and rec.get("source") == stage)
    except Exception as e:                       # the loop must never break the main flow (study design rule)
        print(f"[gsn] pipeline_logger unavailable: {e}", file=sys.stderr)


# ─── helpers ───

def sh(*args, check=True) -> int:
    print("$", " ".join(map(str, args)), file=sys.stderr)
    r = subprocess.run([*map(str, args)], cwd=REPO)
    if check and r.returncode:
        sys.exit(f"[gsn] command failed ({r.returncode}): {args[1] if len(args) > 1 else args[0]}")
    return r.returncode


def slugify(name: str) -> str:
    s = re.sub(r"[^\w.\- ]", "", name, flags=re.UNICODE)
    return re.sub(r"\s+", "-", s.strip())[:60] or "session"


def actor_default() -> str:
    for env, name in (("CLAUDECODE", "claude-code"), ("GEMINI_CLI", "gemini-cli"), ("CODEX_SANDBOX", "codex"),
                      ("GITHUB_COPILOT_CLI", "copilot-cli")):
        if os.environ.get(env):
            return name
    return os.environ.get("GSN_ACTOR", "human-or-shell")


def stage_outputs(sdir: Path, stage: str) -> dict:
    meta = load_meta(sdir)
    files = {"p1-transcribe": ["transcript.srt"], "p1-clean": ["cleaned.srt"],
             "p2-translate": ["transcript.zh-TW.srt"],
             "p3-polish": ["cleaned.md"], "p3-punct": ["cleaned.md"], "p3-hooks": ["cleaned.md"],
             "p4-terms": ["enhanced.md"], "p5-stance": [f"notes_{meta.get('identity', '')}.md"]}.get(stage, [])
    out = {f: sha1_file(sdir / f) for f in files}
    if stage == "p6-matrix":
        run = REPO / "matrix" / "runs" / sdir.name
        for f in ("K.json", "i.json", "claims.json", "diagrams.json", "iv.json", "speakers.json"):
            if (run / f).exists():
                out[f"matrix/runs/{sdir.name}/{f}"] = sha1_file(run / f)
        lj = REPO / "matrix" / "links" / "links.json"
        if lj.exists():
            out["matrix/links/links.json"] = sha1_file(lj)
    return out


def print_results(stage: str, res: list[dict]) -> None:
    for r in res:
        mark = "PASS" if r["ok"] else ("FAIL" if r["level"] == "fail" else "WARN")
        print(f"  {mark:4} {stage:13} {r['name']}" + (f" — {r['detail']}" if r["detail"] else ""))


# ─── markers ───

def task_card(sdir: Path, stage: str) -> dict:
    meta = load_meta(sdir)
    s = STAGE_BY_ID[stage]
    slug = sdir.name
    io = {
        "p2-translate": (f"sessions/{slug}/p2/source.txt", f"sessions/{slug}/p2/zh_parts/*.json"),
        "p3-polish": (f"sessions/{slug}/cleaned.md (Phase A plain text, one cue per line)", f"sessions/{slug}/cleaned.md"),
        "p3-punct": (f"sessions/{slug}/cleaned.md", f"sessions/{slug}/cleaned.md"),
        "p3-hooks": (f"sessions/{slug}/cleaned.md", f"sessions/{slug}/cleaned.md"),
        "p4-terms": (f"sessions/{slug}/cleaned.md", f"sessions/{slug}/enhanced.md"),
        "p5-stance": (f"sessions/{slug}/{'enhanced.md' if 'p4-terms' in meta.get('plan', []) else 'cleaned.md'}",
                      f"sessions/{slug}/notes_{meta.get('identity', '')}.md"),
        "p6-matrix": (f"matrix/runs/{slug}/source.anchors.json", f"matrix/runs/{slug}/ (K.json, i.json, claims.json, …)"),
    }[stage]
    return {"stage": stage, "phase": s["phase"], "title": s["title"], "prompt": s["prompt"],
            "rules": "prompts/rules.md", "input": io[0], "output": io[1],
            "context_file": f"sessions/{slug}/context.txt",
            "identity": meta.get("identity"), "translate_to": meta.get("translate_to"),
            "done_command": f"python3 gsn.py done {slug} {stage} --actor <cli>:<model>",
            "instructions": ("Read CLAUDE.md, prompts/rules.md and the prompt file. Do ONLY this stage. "
                             "Write only the output named above. Then run the done_command; if a gate fails, "
                             "fix the output and run it again (max 3 rounds, then stop and report). "
                             "Never delete this marker, the ledger or the snapshot by hand.")}


def open_stage(sdir: Path, stage: str) -> None:
    """Prepare the input of a judgment stage, snapshot it, write the marker."""
    gsn_dir = sdir / ".gsn"
    gsn_dir.mkdir(exist_ok=True)
    meta = load_meta(sdir)
    base = gsn_dir / f"{stage}.base"
    if stage == "p2-translate":
        cmd = [PY, SRT_ZHTW, "prep", sdir / "cleaned.srt", sdir / "p2"]
        if meta.get("lang") != "en":
            cmd.append("--keep-all")       # srt_zhtw's filter is English-only; a cleaned non-English source keeps every cue
        sh(*cmd)
        shutil.copyfile(sdir / "cleaned.srt", base)
    elif stage == "p3-polish":
        (sdir / "cleaned.md").write_text(gates.phase_a_plaintext(sdir) + "\n", encoding="utf-8")
        shutil.copyfile(sdir / "cleaned.md", base)
    elif stage in ("p3-punct", "p3-hooks", "p4-terms"):
        shutil.copyfile(sdir / "cleaned.md", base)
    elif stage == "p5-stance":
        src = sdir / ("enhanced.md" if "p4-terms" in meta.get("plan", []) else "cleaned.md")
        shutil.copyfile(src, base)
    elif stage == "p6-matrix":
        sh(PY, REPO / "matrix/tools/n.py", "init", sdir, sdir.name, "--title", meta.get("title") or sdir.name,
           "--speaker", meta.get("speaker") or "", check=False)
        shutil.copyfile(sdir / "cleaned.md", base)
    card = task_card(sdir, stage)
    card["base_snapshot"] = rel(base)
    card["created_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    marker_path(sdir, stage).write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    append_ledger(sdir, "open", stage, actor="gsn", base_sha1=sha1_file(base), marker=marker_path(sdir, stage).name)
    print(f"[gsn] {stage} is waiting for an agent → {rel(marker_path(sdir, stage))}")


def next_stage(sdir: Path, after: str | None) -> str | None:
    plan = load_meta(sdir).get("plan", [])
    seq = [s for s in STAGE_ORDER if s in plan]
    if after is None:
        return seq[0] if seq else None
    i = seq.index(after)
    return seq[i + 1] if i + 1 < len(seq) else None


def advance(sdir: Path, after: str) -> None:
    nxt = next_stage(sdir, after)
    if nxt is None:
        meta = load_meta(sdir)
        meta["status"] = "complete"
        save_meta(sdir, meta)
        append_ledger(sdir, "complete", None, actor="gsn")
        print(f"[gsn] ✓ all planned stages done for {sdir.name}. Run: python3 gsn.py audit {sdir.name}")
        return
    if STAGE_BY_ID[nxt]["kind"] == "judgment":
        open_stage(sdir, nxt)


# ─── commands ───

def cmd_new(a) -> int:
    if not a.media and not a.from_srt:
        sys.exit("give a media file or --from-srt")
    src = Path(a.from_srt or a.media).expanduser().resolve()
    if not src.exists():
        sys.exit(f"not found: {src}")
    slug = a.slug or f"{dt.date.today().isoformat()}_{slugify(src.stem)}"
    sdir = SESSIONS / slug
    if sdir.exists():
        sys.exit(f"session exists: {rel(sdir)} — products are never overwritten; pick --slug or remove it")
    sdir.mkdir(parents=True)
    ctx = a.context or ""
    if ctx and Path(ctx).expanduser().is_file():
        ctx = Path(ctx).expanduser().read_text(encoding="utf-8")
    (sdir / "context.txt").write_text(ctx, encoding="utf-8")

    stop = a.stop_at or max(["p3"] + [p for p, on in (("p4", a.terms), ("p5", a.identity), ("p6", a.matrix)) if on])
    last = STOP_AT.index(stop) + 1
    plan = ["p1-transcribe", "p1-clean"]
    if a.translate and a.lang == "zh":
        sys.exit("--translate makes a zh-TW track for a foreign-language talk; this session is --lang zh")
    if a.translate and last >= 2:
        plan.append("p2-translate")
    if last >= 3:
        plan += ["p3-polish", "p3-punct", "p3-hooks"]
    if a.terms and last >= 4:
        plan.append("p4-terms")
    if a.identity and last >= 5:
        plan.append("p5-stance")
    if a.matrix and last >= 6:
        plan.append("p6-matrix")
    meta = {"session_id": slug, "source": src.name, "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "title": a.title or src.stem, "speaker": a.speaker or "", "lang": a.lang, "domain": a.domain,
            "translate_to": a.translate, "identity": a.identity, "phase_a_tool": a.phase_a, "plan": plan, "stop_at": stop, "status": "running"}
    save_meta(sdir, meta)
    append_ledger(sdir, "create", None, actor=actor_default(), plan=plan, source=src.name, context_chars=len(ctx))

    # Phase 1 — tools
    if a.from_srt:
        shutil.copyfile(src, sdir / "transcript.srt")
        how = "imported SRT"
    else:
        if src.suffix.lower() not in MEDIA_EXT:
            print(f"[gsn] warning: {src.suffix} is not a known media extension; trying anyway", file=sys.stderr)
        link = sdir / f"source{src.suffix.lower()}"
        try:
            os.symlink(src, link)          # media stays where it is; sessions/ is gitignored anyway
        except OSError:
            shutil.copy2(src, link)
        if transcribe(sdir, link, a.lang, a.no_prompt, a.chunk_seconds):
            append_ledger(sdir, "tool-fail", "p1-transcribe", actor="gsn")
            sys.exit("[gsn] transcription failed — fix the cause and run `python3 gsn.py resume " + slug + "`")
        how = f"groq whisper-large-v3 ({GROQ[a.lang].name})"
    finish_tool(sdir, "p1-transcribe", how)
    phase_a(sdir, a.domain, a.s2t)
    if load_meta(sdir).get("status") != "complete":
        status_print(sdir)
    return 0


def transcribe(sdir: Path, link: Path, lang: str, no_prompt: bool, chunk_seconds: int | None) -> int:
    """study groq_transcribe(_en).py: <media> <out_dir> <context> → <out_dir>/source.srt → transcript.srt"""
    env = dict(os.environ)
    if no_prompt:
        env["GROQ_NO_PROMPT"] = "1"
    if chunk_seconds:
        env["GROQ_CHUNK_SECONDS"] = str(chunk_seconds)
    print("$", GROQ[lang].name, link.name, file=sys.stderr)
    rc = subprocess.run([PY, GROQ[lang], link, sdir, sdir / "context.txt"], cwd=REPO, env=env).returncode
    out = sdir / f"{link.stem}.srt"
    if rc == 0 and out.exists():
        out.rename(sdir / "transcript.srt")
    return rc if (sdir / "transcript.srt").exists() or rc else 3


def phase_a(sdir: Path, domain: str | None, s2t: bool) -> None:
    """Default: pipeline/phase_a_clean.py (upgrade that won docs/qaqc/tool-comparison.md).
    --phase-a upstream: study SRT/qaqc_srt.py for Chinese; English then keeps every cue and srt_zhtw prep filters."""
    meta = load_meta(sdir)
    dom = ["--domain", domain] if domain else []
    if meta.get("phase_a_tool", "upgrade") == "upgrade":
        sh(PY, REPO / "pipeline/phase_a_clean.py", sdir / "transcript.srt", sdir / "cleaned.srt",
           "--context", sdir / "context.txt", *dom)
        how = "pipeline/phase_a_clean.py (upgrade)"
        if s2t:
            sh(PY, S2T, sdir / "cleaned.srt", "--in-place")
            how += " + s2t_normalize.py"
    elif meta.get("lang") == "en":
        shutil.copyfile(sdir / "transcript.srt", sdir / "cleaned.srt")
        how = "copy (English: hallucination filter runs in srt_zhtw prep)"
    else:
        sh(PY, QAQC_SRT, sdir / "transcript.srt", "-o", sdir / "cleaned.srt", *dom)
        how = "SRT/qaqc_srt.py"
        if s2t:
            sh(PY, S2T, sdir / "cleaned.srt", "--in-place")
            how += " + s2t_normalize.py"
    finish_tool(sdir, "p1-clean", how)


def finish_tool(sdir: Path, stage: str, how: str) -> None:
    res = gates.run_gate(stage, sdir)
    print_results(stage, res)
    loop_log(sdir, stage, how, res)
    if not gates.passed(res):
        append_ledger(sdir, "gate-fail", stage, actor="gsn", gates=res)
        sys.exit(f"[gsn] {stage} gate failed")
    append_ledger(sdir, "tool", stage, actor="gsn", how=how, gates=res, outputs=stage_outputs(sdir, stage))
    advance(sdir, stage)


def cmd_resume(a) -> int:
    """Re-run Phase 1 for a session whose transcription failed half-way (cached chunks are reused)."""
    sdir = session_dir(a.slug)
    meta = load_meta(sdir)
    done = {e["stage"] for e in read_ledger(sdir) if e["action"] in ("tool", "done")}
    if "p1-transcribe" not in done:
        link = next(sdir.glob("source.*"))
        if transcribe(sdir, link, meta.get("lang", "zh"), False, None):
            sys.exit("[gsn] transcription failed again")
        finish_tool(sdir, "p1-transcribe", "groq whisper-large-v3 (resumed)")
    if "p1-clean" not in done:
        phase_a(sdir, meta.get("domain"), False)
    return 0


def status_print(sdir: Path) -> None:
    meta = load_meta(sdir)
    led = read_ledger(sdir)
    done = {e["stage"] for e in led if e["action"] in ("tool", "done")}
    pend = pending_markers(sdir)
    print(f"\nsession {sdir.name}  (plan: {', '.join(meta.get('plan', []))})")
    for s in STAGES:
        if s["id"] not in meta.get("plan", []):
            continue
        state = "done" if s["id"] in done else ("WAITING" if s["id"] in pend else "·")
        print(f"  {state:8} {s['id']:13} {s['title']}")
    if pend:
        print(f"\nnext: {pend[0]} — read {STAGE_BY_ID[pend[0]]['prompt']}, then `python3 gsn.py done {sdir.name} {pend[0]}`")
        print(f"      (task card: python3 gsn.py next {sdir.name})")
    elif meta.get("status") == "complete":
        print(f"\ncomplete — run `python3 gsn.py audit {sdir.name}`")


def cmd_status(a) -> int:
    status_print(session_dir(a.slug))
    return 0


def cmd_next(a) -> int:
    sdir = session_dir(a.slug)
    pend = pending_markers(sdir)
    if not pend:
        print("no pending stage")
        return 0
    print(marker_path(sdir, pend[0]).read_text(encoding="utf-8"))
    return 0


def cmd_check(a) -> int:
    sdir = session_dir(a.slug)
    stages = [a.stage] if a.stage else [s for s in STAGE_ORDER if s in load_meta(sdir).get("plan", [])]
    ok = True
    for st in stages:
        res = gates.run_gate(st, sdir)
        print_results(st, res)
        ok &= gates.passed(res)
    return 0 if ok else 1


def cmd_done(a) -> int:
    sdir = session_dir(a.slug)
    st = a.stage
    if st not in STAGE_BY_ID or STAGE_BY_ID[st]["kind"] != "judgment":
        sys.exit(f"{st} is not a judgment stage")
    pend = pending_markers(sdir)
    if st not in pend:
        sys.exit(f"[gsn] {st} has no pending marker (pending: {pend or 'none'}) — stages run one at a time, in order")
    if pend[0] != st:
        sys.exit(f"[gsn] {st} is not next; finish {pend[0]} first")
    res = gates.run_gate(st, sdir)
    print_results(st, res)
    actor = a.actor or actor_default()
    loop_log(sdir, st, f"gsn.py done ({actor})", res)
    if not gates.passed(res):
        n = sum(1 for e in read_ledger(sdir) if e["action"] == "gate-fail" and e["stage"] == st) + 1
        append_ledger(sdir, "gate-fail", st, actor=actor, round=n, gates=res)
        print(f"[gsn] ✗ {st} gate failed (round {n}). Fix the output and run done again."
              + (" Round 3 reached: STOP and report to the orchestrator (circuit break)." if n >= 3 else ""))
        return 1
    marker_path(sdir, st).unlink()
    outs = stage_outputs(sdir, st)
    for f in outs:                                  # frozen copy of what this gate approved (audit re-checks it)
        if not f.startswith("matrix/") and (sdir / f).is_file():
            shutil.copyfile(sdir / f, sdir / ".gsn" / f"{st}.out.{f}")
    append_ledger(sdir, "done", st, actor=actor, gates=res, outputs=outs)
    meta = load_meta(sdir)
    meta.setdefault("stages", {})[st] = {"status": "done", "actor": actor}
    save_meta(sdir, meta)
    print(f"[gsn] ✓ {st} done ({actor})")
    advance(sdir, st)
    return 0


def cmd_wordcount(a) -> int:
    return subprocess.run([PY, REPO / "pipeline/wordcount.py", a.slug], cwd=REPO).returncode


def cmd_improve(a) -> int:
    """Consumer of the study improvement queue: what is still open, grouped by stage, oldest first."""
    sys.path.insert(0, str(REPO / "scripts"))
    import pipeline_logger as pl
    items = [i for i in pl.list_open() if not a.session or i.get("session") == a.session]
    if not items:
        print("improvement queue: nothing open")
        return 0
    by = {}
    for i in items:
        by.setdefault((i.get("session"), i.get("source")), []).append(i)
    for (sess, src), its in sorted(by.items()):
        print(f"{sess}  {src}  ({len(its)} open)")
        for i in its[:5]:
            print(f"    {i['ts'][:19]}  {i['issue'][:110]}")
    print("\nFix the product (never the gate), re-run `gsn.py done`; a green run closes the stage's items. "
          "A rule/gate defect goes to the observer report as S8.")
    return 1


def cmd_audit(a) -> int:
    return subprocess.run([PY, REPO / "pipeline/audit.py", a.slug], cwd=REPO).returncode


def cmd_headless(a) -> int:
    args = [PY, REPO / "pipeline/headless.py", a.slug, "--cli", a.cli]
    for k in ("model", "effort", "until"):
        if getattr(a, k):
            args += [f"--{k}", getattr(a, k)]
    return subprocess.run(args, cwd=REPO).returncode


def cmd_doctor(a) -> int:
    return subprocess.run([PY, REPO / "pipeline/init.py", *(["--fix"] if a.fix else [])], cwd=REPO).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor"); d.add_argument("--fix", action="store_true")
    n = sub.add_parser("new")
    n.add_argument("media", nargs="?")
    n.add_argument("--from-srt")
    n.add_argument("--slug"); n.add_argument("--title"); n.add_argument("--speaker")
    n.add_argument("--context"); n.add_argument("--lang", default="zh", choices=["zh", "en"]); n.add_argument("--no-prompt", action="store_true")
    n.add_argument("--chunk-seconds", type=int); n.add_argument("--phase-a", choices=["upgrade", "upstream"], default="upgrade"); n.add_argument("--domain"); n.add_argument("--s2t", action="store_true")
    n.add_argument("--translate", choices=["zh-TW"]); n.add_argument("--terms", action="store_true"); n.add_argument("--identity")
    n.add_argument("--matrix", action="store_true"); n.add_argument("--stop-at", choices=STOP_AT)
    sub.add_parser("improve").add_argument("--session")
    for name in ("status", "next", "audit", "resume", "wordcount"):
        sub.add_parser(name).add_argument("slug")
    c = sub.add_parser("check"); c.add_argument("slug"); c.add_argument("stage", nargs="?")
    k = sub.add_parser("done"); k.add_argument("slug"); k.add_argument("stage"); k.add_argument("--actor")
    h = sub.add_parser("headless"); h.add_argument("slug")
    h.add_argument("--cli", required=True, choices=["claude", "gemini", "codex", "copilot", "agy"])
    h.add_argument("--model"); h.add_argument("--effort"); h.add_argument("--until")
    a = ap.parse_args()
    return {"doctor": cmd_doctor, "new": cmd_new, "status": cmd_status, "next": cmd_next, "check": cmd_check,
            "done": cmd_done, "audit": cmd_audit, "wordcount": cmd_wordcount, "improve": cmd_improve, "headless": cmd_headless, "resume": cmd_resume}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
