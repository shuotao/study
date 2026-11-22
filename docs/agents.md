# Agents: roles, substitution, headless, effort routing

Audience: AI agents (and the humans configuring them). Rule: only **measured** assignments are marked
*live*; everything else is *planned*. Evidence lives in `docs/qaqc/eval-effort.md`.

## 1. Roles

| Role | Default model | Responsibility | Hand-off artifact |
|---|---|---|---|
| **Orchestrator** | Fable 5.1 (main interactive session) | read CLAUDE.md, agree phases with the human, open one stage at a time, dispatch implementers, re-run every gate itself, circuit-break after 3 rounds, confirm K (Phase 6) when unattended | marker / task card (`gsn.py next`) |
| **Implementer** | Opus 5.5 for Phase 3–5 prose; Sonnet 5.5 for matrix data workers; Haiku 5.5 for link triage | do exactly one stage, write only its output, run `gsn.py done` | the stage output + ledger `done` entry |
| **Observer** | Sonnet 5.5, fresh context | after the session: ledger + audit + logs → `observer_report.md` with S1–S9 findings | `observer_report.md` |
| **Verifier** (Phase 6) | Opus 5.5, fresh context | lists unsupported / misattributed units in matrix data | `matrix/runs/<slug>/verify/` |
| **Human** | — | context, phase choice, identity, name confirmation, final judgment | — |

Why split them: the model that wrote a text is the worst judge of whether it shortened it. The
implementer never grades itself (gates do), the orchestrator never trusts the implementer's report
(it re-runs gates), and the observer never had the implementer's reasoning in its context.

## 2. One CLI or several — substitution table

Every CLI reads the same constitution (`CLAUDE.md`; `AGENTS.md`/`GEMINI.md` point to it) and drives the
same `gsn.py`. Pick per role whatever you have; the gates do not care who wrote the text.

| Role | Claude Code | Gemini CLI | Codex CLI | Copilot CLI | Antigravity |
|---|---|---|---|---|---|
| Orchestrator | Fable 5.1 / Opus 5.5 | Gemini Pro (latest) | GPT (high reasoning) | any strong model | Gemini Pro |
| Implementer (prose) | Opus 5.5 / Sonnet 5.5 | Gemini Pro | GPT (medium) | Sonnet / GPT | Gemini Pro |
| Implementer (matrix data) | Sonnet 5.5 | Gemini Flash | GPT (medium) | Sonnet | Gemini Flash |
| Observer | Sonnet 5.5 | Gemini Flash | GPT (low/medium) | Sonnet | Gemini Flash |
| Slash commands in repo | `/init` `/good-student-notes` `/observe` (`.claude/skills/`) | `/init` `/notes` `/observe` (`.gemini/commands/`) | none: say "run init" (AGENTS.md) | none: AGENTS.md | `/init` `/notes` `/observe` (`.agent/workflows/`) |

Rules for mixing:
- The observer should come from a **different context** than the implementer; a different model family is
  even better (catches correlated blind spots).
- Never use the same process for implementer and observer of the same session.
- Image generation is not part of this repo (no CLI here has an image tool on OAuth).

## 3. Headless (unattended) — the implementer loop across CLIs

`python3 gsn.py headless <slug> --cli <cli> [--model M] [--effort E] [--until STAGE]` runs each pending stage
in a fresh headless process, re-runs the gate itself, feeds exact failures back, and circuit-breaks after 3
rounds. Logs: `sessions/<slug>/.gsn/headless/`. Underlying commands (all OAuth, no API key):

| CLI | Command used | Effort flag |
|---|---|---|
| Claude Code | `claude -p "<task>" --permission-mode acceptEdits --allowedTools Read Edit Write Glob Grep "Bash(python3 *)" --model M` | `--effort low…max` |
| Gemini CLI | `gemini -m M --approval-mode yolo "<task>"` | (model choice) |
| Codex CLI | `codex exec -m M --sandbox workspace-write -C <repo> "<task>"` | `-c model_reasoning_effort=…` |
| Copilot CLI | `copilot -p "<task>" --allow-all-tools --model M` | `--effort …` |
| Antigravity | `agy --mode accept-edits --model M -p "<task>"` | `--effort …` |

Observer headless: `claude -p "/observe <slug>" --model sonnet --permission-mode acceptEdits --allowedTools Read Write Glob Grep "Bash(python3 *)" "Bash(git status*)" "Bash(git diff*)"` (or `gemini "/observe <slug>"`).
`yolo` / `--allow-all-tools` give the agent your shell inside the repo: run headless only in this repo,
on your own material.

**Antigravity notes (measured in study, 2026-11-22):**
- **`-p` comes last.** `agy -p --model X "<task>"` makes `-p` take the next token (`--model`) as its prompt and
  exits with an error. Put every flag first and `-p "<task>"` at the end, or write `-p='<task>'`. `-p "<task>"`
  directly followed by other flags also works (the prompt is `-p`'s value), but the flags-first order is what
  `pipeline/headless.py` and study's `describe_images.run_agy` use. The same applies to `antigravity` (same CLI).
- **Model ids come from `agy models`**, not from memory — Antigravity retires models (study lost
  `Gemini 3.5 Flash` overnight on 2026-09-01). As of 2026-11-22 it lists `gemini-4-hydrogen-{low,medium,high,xhigh}`,
  `gemini-4-neon-{low,medium,high,xhigh}`, `gemini-4-argon-{low,medium,high}`, `gemini-3.8-flash-{low,medium,high}`
  (and older Flash), `gemini-3.1-pro-{low,high}`, `claude-{opus,sonnet}-5-5-{low,medium,high}`. study moved its image
  stage to `gemini-4-hydrogen-medium`; this repo has no image stage, and the Phase 2 batch translator
  (`srt_translate_zhtw.py`, upstream, unchanged) still defaults to `gemini-3.8-flash-medium` and falls back along its
  `MODEL_PREFERENCE` when that id is missing. Neon / Argon are listed but unmeasured here.
- **Parallel workers are safe for Phase 2.** `srt_translate_zhtw.py <p2-dir> --range LO-HI` translates only cues
  LO–HI; part files are named by cue index, so several workers on one talk never collide, and re-running fills
  only the gaps. In study, multiple workers per lecture were ~6× faster than one. With 11 concurrent agy
  sessions about 5 % of calls failed with `failed to start conversation: backend returned an empty conversation id`;
  the built-in per-batch retry recovered all of them. Run `zh_parts_check.py` once after all workers finish.

### Orchestration pattern: edit plan instead of rewrite (p3-polish)

For long texts, a pattern that worked in study (2026-11-22): the orchestrator gives a worker subagent the
plain text and asks for an **edit plan** in JSON — headings to insert (after which line), speaker labels,
paragraph splits/merges, and exact `{"from": …, "to": …}` replacements (names, punctuation, glyphs) — instead of
the rewritten file. The orchestrator applies the plan deterministically and then runs the gates itself
(`gsn.py done`: word-count band, CJK ratio, `para_len_check.py`). Because the worker never retypes the speaker's
words, it cannot silently drop or paraphrase them, and a bad plan fails on a specific entry instead of somewhere
in a rewritten text. There is no tool for this in the repo yet; a one-off apply script stays in the session
(gitignored), and the stage still closes only through `gsn.py done`.

## 4. Effort routing (live = measured)

Filled from `docs/qaqc/eval-effort.md`. Until a row says *live*, treat it as planned.

| Stage | Recommended | Status | Evidence |
|---|---|---|---|
| p2-translate | Sonnet 5.5, effort medium | planned | — |
| p3-polish / p3-punct / p3-hooks | **Opus 5.5 · low** (budget: Sonnet 5.5 · low; not Haiku) | live (n = 1, excerpt; 6 configs) | `docs/qaqc/eval-effort.md` — all 6 configs passed every gate first round; blind read ranked opus·low 1st, haiku·medium last; higher effort did not improve quality |
| p4-terms / p5-stance | Opus 5.5, effort medium | planned | — |
| p6 matrix workers | Sonnet 5.5 (K, I, claims, diagrams, iv.json, links type+why), Haiku 5.5 (link vs exclude) | live in the source project (N, 2026-10-13; 10/10 runs for K and I) | `matrix/SPEC.md` §10 |
| Observer | Sonnet 5.5, effort medium | planned | — |
