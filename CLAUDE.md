# CLAUDE.md — Good-Student Notes (好學生筆記 + 好學生矩陣), CLI edition

The single authoritative specification for every AI agent working in this repository.
`AGENTS.md` and `GEMINI.md` contain one line, `CLAUDE.md`: whatever CLI you are, you are bound by this file.
Humans read `README.md` (Traditional Chinese). **Text for agents is English; text for humans and every
product written from a Chinese talk is Traditional Chinese (zh-TW) with full-width punctuation.**

## What this repo does

Audio or video of a talk → six phases → products a learner can read at four depths. Origin: the talk
「說話與聽話」 (AI Earth Meetup, 2026-10-21; `examples/talk-context/`), whose three take-aways are the
architecture of this repo:
1. **Split the task into phases; each phase does one thing.**
2. **Deterministic work goes to tools, judgment goes to AI, the final decision goes to a human.**
3. **Keep every phase's product: each one is learning material.**

| Phase | Stage id(s) | Kind | Product (`sessions/<slug>/`) |
|---|---|---|---|
| 1 | `p1-transcribe`, `p1-clean` | tool | `transcript.srt` (immutable), `cleaned.srt` |
| 2 | `p2-translate` (optional) | judgment | `transcript.zh-TW.srt` (second subtitle track next to `cleaned.srt`) |
| 3 | `p3-polish` → `p3-punct` → `p3-hooks` | judgment | `cleaned.md` — the full text (quadrant II) |
| 4 | `p4-terms` (optional) | judgment | `enhanced.md` |
| 5 | `p5-stance` (optional) | judgment | `notes_<identity>.md` |
| 6 | `p6-matrix` (optional) | judgment (orchestrated) | `matrix/runs/<slug>/` I · II · III · IV pages |

Default stop: Phase 3. Every product is a valid end point.

## Iron rules (violations are bugs — fix the architecture, not the prompt)

1. **Zero omission.** Never summarise, condense or rewrite the speaker's words. Supplements live in `>` blocks
   beside the text. Rulebook: `prompts/rules.md` (§ R0–R10). Gates: `pipeline/gates.py`.
2. **The SRT is evidence.** `transcript.srt` is never modified. An LLM never reads or writes a timecode;
   timed outputs go through `scripts/lang/en/srt_zhtw.py` (split → text only → re-attach → byte check).
3. **Tools for deterministic work, LLM for judgment.** Transcription, cleaning, full-width punctuation,
   counting, assembling, rendering: tools. If you notice yourself doing mechanical work by hand, stop and use
   (or write) a tool.
4. **One stage at a time, through markers.** `gsn.py` writes `.<stage>.pending.json`; you do that stage
   only; `python3 gsn.py done <slug> <stage> --actor <cli>:<model>` clears it **only if the gate is green**
   and opens the next one. Never delete a marker, snapshot (`.gsn/`) or ledger line by hand; never bundle
   stages. `gsn.py audit` proves all of this afterwards from a hash-chained ledger.
5. **Never trust "I checked".** The orchestrator re-runs gates itself; the auditor re-runs every gate on
   the frozen outputs. A gate that seems wrong is reported (`S8` in the observer report), never bypassed;
   no gate has a force flag.
6. **No LLM API keys.** Judgment runs inside an agent CLI on its OAuth login (Claude Code, Gemini CLI, Codex,
   Copilot, Antigravity). The only key is `GROQ_API_KEY` for Whisper, read from `.env` at the point of use.
7. **Secrets and material never reach git.** `.env`, keys, raw media, `sessions/`, `matrix/runs|links|vault/`
   are gitignored; `pipeline/secret_scan.py` runs as the pre-commit hook. Never print a key's value.
8. **Names come from authorities** (`context.txt`, agenda), never guessed; doubts go to `corrections.json`.
9. **Max 3 repair rounds per stage**, then circuit-break: stop and report to the orchestrator / user.
10. **Upstream tools are not edited here.** This repo is the `cli-edition` branch of study. The field-proven study
    tools (`docs/tools.md` § Upstream) stay byte-identical (`docs/upstream.sha1`, enforced by tests). A new tool
    that replaces one is a *candidate upgrade*: it becomes the default only after it wins a head-to-head
    comparison on real sessions (`docs/qaqc/tool-comparison.md`).
11. **Word counts are the backbone of QAQC.** Same basis on both sides (E1), traced from ALL original cues (E4),
    95–105 % after polishing. `gsn.py wordcount <slug>` prints the chain; audit A9 enforces it.
12. **Close the loop.** Gate results feed study's `pipeline_logger` (log → check → improvement queue);
    `gsn.py improve` lists what is open. Fix products, not gates; a defective gate is an S8 finding.

## How to operate

```bash
python3 gsn.py doctor                    # environment (= /init)
python3 gsn.py new <media> --context "speaker, company, product names" [--translate zh-TW] [--terms] \
        [--identity 建築師] [--matrix] [--stop-at p3]
python3 gsn.py status <slug>             # which stage waits
python3 gsn.py next <slug>               # task card: prompt, input, output, done command
# … do the stage per its prompt …
python3 gsn.py done <slug> <stage> --actor claude-code:opus-5.5
python3 gsn.py wordcount <slug>          # word-count chain, original → every stage
python3 gsn.py audit <slug>              # all green before you report "done"
python3 gsn.py headless <slug> --cli claude --model sonnet --effort medium   # unattended implementer loop
```
Stage prompts: `prompts/phase*.md`. Phase 6 spec: `matrix/SPEC.md` (+ `matrix/prompts/`).
When the session ends, the observer writes `observer_report.md` (`prompts/observer.md`).

## Roles (details, substitutions and measured effort: `docs/agents.md`)

| Role | Default | Does | Never does |
|---|---|---|---|
| Orchestrator | **Fable 5.1** (main session) | plans the session, dispatches one stage at a time, re-runs gates, decides circuit breaks, confirms K when unattended | write products itself when a worker is assigned |
| Implementer | **Opus 5.5** (Phase 3–5 text) / Sonnet 5.5 (matrix workers) | does exactly one stage per task card, runs `gsn.py done` | touch other stages, markers, ledger, gates |
| Observer | **Sonnet 5.5**, fresh context | reads ledger + audit + logs, writes `observer_report.md`, classifies shortcuts S1–S9 | fix products |
| Human | you | chooses phases and identity, supplies context, confirms names and K, makes the final call | — |

A single-agent setup is fine: one CLI plays all roles, but it still goes through markers, gates and audit.

## Finishing a piece of work (definition of done)

- `python3 gsn.py audit <slug>` all green, observer report written, verdict stated honestly.
- Changing this repo's code: `python3 -m unittest discover tests` green (includes the docs-sync and secret
  tests); `python3 pipeline/secret_scan.py --all` clean.
- Report failures as failures; report skipped steps as skipped.

## Where things are

| Path | What |
|---|---|
| `gsn.py` | single entry point (doctor, new, status, next, check, done, audit, headless, resume) |
| `pipeline/` | Phase 1–5 tools, gates, ledger, audit, headless driver, secret scan — registry `docs/tools.md` |
| `prompts/` | rulebook `rules.md`, one prompt per stage, `observer.md` |
| `matrix/` | Phase 6: `SPEC.md`, `tools/`, `prompts/`, `runs/` + `links/` + `vault/` (generated, gitignored) |
| `dict/` | typo and hallucination dictionaries for Phase A |
| `docs/agents.md` | roles, CLI substitution, headless commands, effort routing with eval evidence |
| `docs/qaqc/` | how this repo was built: build log, eval results, observer report |
| `examples/talk-context/` | fixture: the origin talk as a raw SRT (`transcript.srt`, `excerpt.srt`) + `context.txt` |
| `sessions/<slug>/` | your sessions (gitignored): products, `ledger.jsonl`, `.gsn/` snapshots, reports |
