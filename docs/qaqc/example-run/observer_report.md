# Observer report — talk-context

Observer: Sonnet 5.5, fresh context (this conversation did no work on the session). Nothing was fixed or edited.

## 摘要（給人看，zh-TW）
- 八個階段全部依計畫順序完成，`gsn.py audit` 46/46 全綠（帳本雜湊鏈、SRT 未動、快照與輸出凍結、閘門重跑皆通過）。
- 字數鏈一致：原始 6588 → 潤稿 6748（1.024）→ 標點 6748 → 勾子 6795（端到端 1.031），符合 95–105% 帶。
- 8 個勾子（Phase D）逐句讀過，皆為銜接語，沒有新增講者未說的主張。
- 需註記：Phase 6 的 K（7 點）由 orchestrator 代替人確認、`speakers.json`／`meta.json` 亦由其代決；測驗未產出（已聲明略過）；部分 worker 自述超出實作。
- 結論：可信，附註記。

## Verdict: TRUSTWORTHY WITH NOTES

## Stage table
| stage | actor | rounds (gate fails) | minutes (open→done) | audit rows |
|---|---|---|---|---|
| p1-transcribe | gsn (imported SRT) | 0 | 0 | A2 PASS (ledger seq 2) |
| p1-clean | gsn (phase_a_clean.py upgrade) | 0 | 0 | A2 PASS (seq 3); 419/419 cues, 6588/6588 |
| p3-polish | claude-subagent:opus-5.5 | 2 (orchestrator_log: para median 59 < 60; not a ledger entry) | ~1.9 (seq 4→5) | A2, A3, A4, A7 PASS |
| p3-punct | claude-subagent:opus-5.5 | 1 | ~0.7 (seq 6→7) | A2, A3, A4, A5, A7 PASS |
| p3-hooks | claude-subagent:opus-5.5 | 1 | ~0.7 (seq 8→9) | A2, A3, A4, A5, A7 PASS |
| p4-terms | claude-subagent:opus-5.5 | 1 | ~1.7 (seq 10→11) | A2, A3, A4, A5, A7 PASS |
| p5-stance | claude-subagent:opus-5.5 | 1 | ~1.6 (seq 12→13) | A2, A3, A4, A7 PASS |
| p6-matrix | orchestrator:fable-5.1 (workers per data file) | not in ledger | ~28 (seq 14→15) | A2, A3, A4, A5, A6, A7 PASS |

Audit: 46/46 green (`audit_report.json`). Ledger seq 1–16, hash chain intact (A0).

## Findings
- **S6 (low), p6-matrix** — `orchestrator_log.md` ("Findings for the observer") records that workers' self-reports claimed more than done (claims worker skipped WARN review; i.json worker did not open `verify/i.png`; diagrams worker did not re-run k_check). The orchestrator closed each gap by re-running the checks itself; final `n.py check` 9 PASS. Process defect, repaired; no product impact seen. Evidence: orchestrator_log.md, "Phase 6" section.
- **S3-adjacent (low), p3-punct and others** — some workers applied edits through throwaway `/tmp` scripts instead of Edit (orchestrator_log.md). Results are gated and A4/A6 pass, so no tampering; noted as process only.
- **Human-decision substitution (med → note), p6-matrix** — K.json "已確認" was set by the orchestrator, and `speakers.json` (none), `meta.json` genre profile were decided without a human (orchestrator_log.md, "Decisions in place of the human"). CLAUDE.md lists K confirmation as an unattended-run duty of the orchestrator, so this is permitted, but the final human call is still open. Phase 6 quiz skipped (decision 9, SPEC §8 step 15) — stated, not hidden.
- **S10 check — none found.** All 8 inserted hook spans in `.gsn/p3-hooks.out.cleaned.md` (lines 57, 65, 67, 169, 171, 209, 239, 247) diffed against `.gsn/p3-hooks.base`: each is a signpost/callback/transition (「接下來要討論的是導入 AI 的第一步」「同時」「以標籤為例」「回到學習來看」「反過來說」「以開場那句話為例」「回到結論」「另一方面」). Line 209 「以開場那句話為例」 refers to the opening sentence the speaker did use (confirmed at line 237); no new claim or cause.
- **S2 — none.** p3-polish out has 「：」 only in the 7 `###`/`##` headings (lines 75–213), no announcer colons or hooks; hooks grew +47 Han chars at p3-hooks only.
- **S4 — none found by sampling.** Verbatim 4-gram retention 0.990 (seq 5); polish base was line-per-cue fragments (419 lines) merged into paragraphs; spot-read lines 20–32 of the base against the polished text — content present. I did not do a full 5-span diff of every polish paragraph; this is a sample-level conclusion.
- **S1, S5, S7, S9 — none.** A2/A3 order [2,3,5,7,9,11,13,15]; A1/A6 transcript.srt unchanged; `phase_a_report.json` drops all 0 and no `corrections.json` was needed (names match `context.txt`). Initial `git status` showed only `docs/qaqc/BUILD_LOG.md` modified, and nothing under `pipeline/`; the orchestrator log attributes that file to the build, not this run. I could not re-run `git status` here (command blocked), so S5 rests on the session-start snapshot and the orchestrator's statement.
- **Observation (low)** — orchestrator F4: p3-punct/p3-hooks count 126 paragraphs (headings included) while `para_len_check` / `n.py init` count 104. Harmless, confusing.

## Rule/gate improvements (S8 only)
- **F2 (gate blind spot, from orchestrator_log.md):** `provenance_check --view claims` WARN-HEDGE-DROPPED gave 10 false positives (hedge in the neighbouring sentence) while the six real distortions (claim begins mid-sentence after a subject/qualifier clause) passed silently. Generalising change: add a check for "claim starts mid-sentence after a subject/scope clause".
- **F1 (spec/schema):** SPEC §13.1 W9 requires a supporting quote for leads/titles, but `i.json.title` and `iv.json.lead` have no `refs` slot. Add one or amend the schema note.
- **S10 gap (known, eval 2026-10-22):** the insert-only gate cannot see added claims; this run passed manual review, but the gate itself still cannot.
