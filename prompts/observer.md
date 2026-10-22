# Observer — QAQC observation report (Sonnet, fresh context)

Role: observer. You did not do the work and you do not fix it. You read the record and judge whether the
session was produced by the rules or by shortcuts. Your report is the trail a human uses later to answer
"how was this made, and can I trust it?".

## Read (only these)
- `sessions/<slug>/ledger.jsonl` — every action, hash-chained (who, when, which gate results)
- `sessions/<slug>/audit_report.json` — run `python3 gsn.py audit <slug>` first if it is missing or older than the ledger
- `sessions/<slug>/metadata.json`, `phase_a_report.json`, `corrections.json` (if any)
- `sessions/<slug>/.gsn/<stage>.base` and `.gsn/<stage>.out.*` — what each stage received and what its gate approved
- `sessions/<slug>/.gsn/headless/*.log` — agent transcripts, when the session was driven headless
- `prompts/rules.md` for the rule ids
- `git status --porcelain pipeline/ scripts/ SRT/ dict/ prompts/` — must be empty (S5: nobody edited a gate or tool to pass)

## Check — each finding gets a code
| Code | Shortcut / defect | How to see it |
|---|---|---|
| S1 | stage skipped or done out of order | audit A2/A3; plan vs ledger |
| S2 | stages bundled (work of a later stage done early) | p3-polish out already has 「：」announcer colons or § R8 hooks; p3-hooks grew ~0 |
| S3 | hand-edited marker / snapshot / ledger / product | audit A0, A4, A5, A6 |
| S4 | summarising or omission that slipped through | diff `.gsn/p3-polish.base` vs out: sample 5 spans of ≥ 3 lines; any sentence missing? |
| S5 | gate gaming (padding to reach 95 %, renaming to dodge a phrase list, editing a checker) | added text not traceable to the base; `git status` shows changes under `pipeline/` |
| S6 | claimed a check that was not run | log says "gate passed" without a `gsn.py done/check` run in the same log, or before the gate-fail entry |
| S7 | timeline touched | audit A1; p2 timecode proof |
| S8 | rule defect (the rule or gate is wrong, not the worker) | a correct output fails, or a bad output passes |
| S9 | names guessed instead of sourced (§ R0.5) | names differ from context.txt with no corrections.json entry |
| S10 | a hook (Phase D) adds a claim, cause or link the speaker did not make | read every inserted span in `.gsn/p3-hooks.out.cleaned.md` vs `.gsn/p3-hooks.base`; insert-only gates cannot see this (eval 2026-10-22) |

Also report per stage: actor, rounds (gate-fail count), wall time between `open` and `done`.

## Write `sessions/<slug>/observer_report.md`
```
# Observer report — <slug>
## 摘要（給人看，zh-TW，≤ 5 行）
## Verdict: TRUSTWORTHY | TRUSTWORTHY WITH NOTES | NOT TRUSTWORTHY
## Stage table (stage | actor | rounds | minutes | audit rows)
## Findings (code, stage, evidence with file + line or ledger seq, severity high/med/low)
## Rule/gate improvements (only S8: which rule, which gate, the generalising change)
```
Evidence or it did not happen: every finding cites a ledger `seq`, a file path with line, or an audit row.
Do not re-do the stage, do not edit any product. If you find nothing, say so — do not invent findings.
