#!/usr/bin/env python3
"""headless.py — drive pending judgment stages through a headless agent CLI (the implementer).

Every supported CLI authenticates with its own OAuth login, so no LLM API key is needed:

  claude   claude -p … --model M --effort E --permission-mode acceptEdits --allowedTools …
  gemini   gemini -m M --approval-mode yolo "…"
  codex    codex exec -m M -c model_reasoning_effort=E --sandbox workspace-write "…"
  copilot  copilot -p … --model M --effort E --allow-all-tools
  agy      agy -p … --model M --effort E --mode accept-edits   (Antigravity)

Loop per stage (this script plays the orchestrator's mechanical part):
  1. hand the task card to the agent (fresh process = fresh context)
  2. when the agent exits, re-run the stage gate HERE — never trust "I ran it"
  3. green → `gsn.py done` (if the agent did not already); red → send the exact failures back
  4. max 3 rounds per stage, then circuit-break: stop and report, no silent retry
Transcripts go to sessions/<slug>/.gsn/headless/<stage>.r<N>.log for the observer.

Usage: python3 pipeline/headless.py <slug> --cli claude [--model sonnet] [--effort medium] [--until p3-hooks]
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import gates  # noqa: E402
from pipeline.common import REPO, STAGE_BY_ID, STAGE_ORDER, append_ledger, marker_path, pending_markers, session_dir  # noqa: E402

MAX_ROUNDS = 3
TIMEOUT_S = int(os.environ.get("GSN_HEADLESS_TIMEOUT", "3600"))


def command(cli: str, prompt: str, model: str | None, effort: str | None) -> list[str]:
    if cli == "claude":
        c = ["claude", "-p", prompt, "--permission-mode", "acceptEdits",
             "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", "Bash(python3 *)"]
        return c + (["--model", model] if model else []) + (["--effort", effort] if effort else [])
    if cli == "gemini":
        return ["gemini", *(["-m", model] if model else []), "--approval-mode", "yolo", prompt]
    if cli == "codex":
        return ["codex", "exec", *(["-m", model] if model else []),
                *(["-c", f"model_reasoning_effort={effort}"] if effort else []),
                "--sandbox", "workspace-write", "-C", str(REPO), prompt]
    if cli == "copilot":
        return ["copilot", "-p", prompt, "--allow-all-tools", *(["--model", model] if model else []),
                *(["--effort", effort] if effort else [])]
    if cli == "agy":
        return ["agy", "-p", prompt, "--mode", "accept-edits", *(["--model", model] if model else []),
                *(["--effort", effort] if effort else [])]
    raise SystemExit(f"unknown cli {cli}")


def build_prompt(slug: str, stage: str, actor: str, feedback: str) -> str:
    card = marker_path(session_dir(slug), stage).read_text(encoding="utf-8")
    p = (f"You are the IMPLEMENTER for one stage of the Good-Student Notes pipeline in this repository.\n"
         f"Read CLAUDE.md first, then prompts/rules.md and {STAGE_BY_ID[stage]['prompt']}.\n"
         f"Do only stage {stage} for session {slug}. Task card:\n{card}\n"
         f"When the output is written, run: python3 gsn.py done {slug} {stage} --actor {actor}\n"
         f"If it prints FAIL lines, fix the output and run it again. Do not touch any other stage, marker, "
         f"snapshot (.gsn/) or ledger.jsonl. Reply with one line: what you produced and the final gate result.")
    if feedback:
        p += f"\n\nPREVIOUS ROUND FAILED. The orchestrator re-ran the gate and got:\n{feedback}\nFix exactly these."
    return p


def run_agent(cmd: list[str], log: Path) -> int:
    """Output goes to a file and the CLI runs in its own process group: a pipe + timeout can deadlock
    when the CLI leaves grandchildren behind, so we kill the whole group on timeout."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd[:2]) + " …\n\n")
        f.flush()
        p = subprocess.Popen(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT, start_new_session=True,
                             env={**os.environ, "GSN_ACTOR": cmd[0]})
        try:
            return p.wait(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            time.sleep(5)
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGKILL)
            return 124


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--cli", required=True)
    ap.add_argument("--model")
    ap.add_argument("--effort")
    ap.add_argument("--until", help="stop after this stage")
    a = ap.parse_args()
    sdir = session_dir(a.slug)
    actor = f"{a.cli}:{a.model or 'default'}:{a.effort or 'default'}"

    while True:
        pend = pending_markers(sdir)
        if not pend:
            print("[headless] nothing pending")
            return 0
        stage = pend[0]
        feedback = ""
        for rnd in range(1, MAX_ROUNDS + 1):
            t0 = time.time()
            log = sdir / ".gsn" / "headless" / f"{stage}.r{rnd}.log"
            rc = run_agent(command(a.cli, build_prompt(a.slug, stage, actor, feedback), a.model, a.effort), log)
            secs = round(time.time() - t0)
            append_ledger(sdir, "headless", stage, actor="orchestrator", cli=actor, round=rnd, exit=rc, seconds=secs,
                          log=str(log.relative_to(sdir)))
            if not marker_path(sdir, stage).exists():
                res = gates.run_gate(stage, sdir) if stage != "p6-matrix" else gates.run_gate(stage, sdir)
                print(f"[headless] {stage} round {rnd}: agent ran done ({secs}s); orchestrator re-check "
                      f"{'PASS' if gates.passed(res) else 'FAIL'}")
                if not gates.passed(res):
                    print("[headless] the output changed after done — stop", file=sys.stderr)
                    return 1
                break
            rc2 = subprocess.run([sys.executable, REPO / "gsn.py", "done", a.slug, stage, "--actor", actor],
                                 cwd=REPO, capture_output=True, text=True)
            if rc2.returncode == 0:
                print(f"[headless] {stage} round {rnd}: PASS (done run by orchestrator, {secs}s)")
                break
            feedback = "\n".join(l for l in rc2.stdout.splitlines() if "FAIL" in l)[:3000]
            print(f"[headless] {stage} round {rnd}: FAIL\n{feedback}")
        else:
            append_ledger(sdir, "circuit-break", stage, actor="orchestrator", cli=actor)
            print(f"[headless] circuit break: {stage} failed {MAX_ROUNDS} rounds — stop and report", file=sys.stderr)
            return 2
        if a.until and STAGE_ORDER.index(stage) >= STAGE_ORDER.index(a.until):
            return 0


if __name__ == "__main__":
    sys.exit(main())
