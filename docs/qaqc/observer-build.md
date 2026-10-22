# Observer report — repository build

Observer: Sonnet 5.5, fresh context. Nothing was fixed or edited except this file. Checked at commit `e52ef5e`
(branch `cli-edition`, working tree: `docs/qaqc/BUILD_LOG.md` modified and uncommitted).

Commands I ran myself: `python3 -m unittest discover tests` (18 tests, OK); `python3 pipeline/secret_scan.py --all`
(clean); `shasum -c docs/upstream.sha1` (21/21 OK) plus a `cmp` of all 21 files against
`~/Desktop/study` (all identical); `python3 pipeline/audit.py talk-context` (46/46 green);
`python3 pipeline/wordcount.py talk-context` (PASS); `git ls-remote https://github.com/shuotao/study`;
`git log --all` scan for key patterns.

## 摘要（zh-TW，給人看，≤ 6 行）
- 程式、測試、機敏掃描、原版工具位元相同（21/21）、字數鏈與 audit 都是我自己重跑過，結果與文件一致。
- 目前追蹤的檔案沒有金鑰、媒體或 sessions；歷史裡只有 study 繼承來的 Firebase 公開 web 設定（非密鑰）。
- 主要缺口：範例跑的證據（`docs/qaqc/example-run.md`、`sessions/talk-context/`）沒有進 repo，README 卻寫「完整範例跑在 docs/qaqc/」。
- 重做輪數只有 orchestrator_log 有記，帳本是 0 次失敗；`tool-comparison.json` 在修正後沒重跑；BUILD_LOG 有幾處過期。
- 跨 CLI（gemini/codex/copilot/agy）與 Groq 走 `gsn.py new <音檔>` 的整條路沒有實跑證據，只有 Claude 與 `--from-srt`。
- 結論：可信，附註記（0 高、5 中、7 低）。

## Verdict: TRUSTWORTHY WITH NOTES

## Requirements check

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Clone-and-use CLI; /init; CLAUDE/GEMINI/AGENTS; English agent text; zh-TW README (Groq signup, roles/substitution, headless) | **Met, with one untested part** | `AGENTS.md` and `GEMINI.md` are the one line `CLAUDE.md` (tests/test_repo_hygiene.py:`test_pointer_files`); `.claude/skills/init`, `.gemini/commands/init.toml`, `.agent/workflows/init.md` exist; README §1 Groq, §5 substitution table, §6 headless. `gsn.py doctor` runs (8/11 on this machine: no `.env`, no hook, as expected). The non-Claude CLIs have never been run (B8). Matrix `.py` keep Chinese comments (BUILD_LOG "Known limitations", disclosed). |
| 2 | Reuse mature study tools; compare new ones, adopt only if better | **Met (verified)** | 21 upstream files byte-identical to study working tree (my `cmp` loop). `git diff bdaca2b..HEAD -- scripts SRT dict` shows only 2 added files, no modified upstream tool. Three rewrites compared in `docs/qaqc/tool-comparison.md`; 1 adopted, 2 rejected, with real Groq calls. Caveats: B4, B5. |
| 3 | Branch from the original (lineage) | **Met, naming differs** | `git log` contains `bdaca2b` and the study history, 6 commits on top. On GitHub `shuotao/study` the only refs are `HEAD` and `refs/heads/main`, both `e52ef5e`; there is no `cli-edition` ref there, and the local `origin` is `GENAI.git` (B10). CLAUDE.md rule 10 and README §12 say "the `cli-edition` branch of study". |
| 4 | Word-count QAQC; log→check→improve loop carried over | **Met** | `pipeline/wordcount.py` + audit A9 (re-ran: PASS, 6588→6795, 1.031); band 0.95–1.05 enforced as a fail gate at `pipeline/gates.py` (`gate_p3_polish`); E4 base is the original SRT. `scripts/pipeline_logger.py` unchanged, wired in `gsn.py:65 loop_log`. Weak points: Phase A band is warn-only; counting includes heading text (B7). |
| 5 | Roles Fable / Opus / Sonnet; traceable records; catch shortcuts | **Partly** | Hash-chained ledger + audit A0–A9 are real and re-run green; tamper tests exist (tests/test_pipeline.py `test_2/3/4`). But the repo itself was built by an Opus orchestrator, not Fable (BUILD_LOG "Roles", disclosed), repair rounds are not in the ledger (B2), and the chain is not tamper-proof against a full rewrite (B6). |
| 6 | No secrets / raw media uploaded | **Met for the tree; history inherited** | `git ls-files` (133 files): no media, no `.env`, `sessions/` only README, `matrix/runs|links|vault` untracked; `.gitignore` covers them; secret_scan clean; no email addresses in HEAD. History: only a Firebase web config with `AIza…` key in study's `admin/firebase-config.js` (file comment says it is public by design). Pre-commit hook is not installed in this checkout (`doctor` FAIL) (B10). |
| 7 | Use /eval to optimise effort | **Partly** | `docs/qaqc/eval-effort.{md,json}`: numbers in the md table match the json for all 6 configs (I compared ratio, 4-gram, para median, colons, minutes). `trigger-results.json` 18/18 pass (9 positive, 9 negative, 3 runs each). But n = 1 per config on a 936-char excerpt, only Phase 3 measured, other rows in `docs/agents.md` §4 are marked "planned" (honest), and it used a bespoke harness (`pipeline/eval_effort.py`) rather than a repeatable skill-eval runbook. Judge was an Opus model ranking an Opus config first (B11). |

## Findings

Severity count: **high 0, med 5, low 7** (12 findings).

**B1 (med) — Example-run evidence is claimed in docs but not in the repo.**
README §12 table: new orchestration layer "完整範例跑在 `docs/qaqc/`"; BUILD_LOG B9 cites `docs/qaqc/example-run.md`; B6 cites a `smoke` session ledger "audit 44/44". `ls docs/qaqc` has no `example-run.md` (only `example-run-orchestrator-prompt.md`); `sessions/` is gitignored, so `sessions/talk-context/` (ledger, audit, wordcount, orchestrator_log, observer_report) exists only on this machine; no `smoke` session exists anywhere. A cloner cannot check the headline example. I verified it locally (audit 46/46, wordcount PASS), but the published repo does not carry it.

**B2 (med, S6-adjacent) — Repair rounds are not traceable from the ledger.**
`orchestrator_log.md` says p3-polish took 2 rounds (paragraph median 59 < 60). `ledger.jsonl` (seq 4→5) has no `gate-fail` entry and `pipeline_log.jsonl` shows `p3-polish … failed: 0`. `gsn.py:374 cmd_check` prints results but writes nothing; only `cmd_done` records failures (`gsn.py:398-401`). Audit A8 and the observer's "rounds = gate-fail count" therefore read 0 for a stage that the orchestrator says failed once. This undermines "records traceable" (req. 5) and the improvement queue (a failed `check` never opens an item). The example observer report already notes it (row p3-polish) but its other rows put "1" in a column headed "gate fails" when the ledger count is 0.

**B3 (low) — BUILD_LOG is partly stale and uncommitted.**
B5 cites `pipeline/transcribe_groq.py`; it now exists only as `pipeline/candidates/transcribe_groq.py` and `gsn.py` never calls it. B7 says "17 OK"; the suite now has 18. B1 says "5 cli-edition commits"; there are 6 (`4b2c2ca`…`e52ef5e`). Rows B11–B13 and D9–D12 are only in the working tree (`git diff` shows them), not in a commit. B10 points to this file, which did not exist until now.

**B4 (med) — Comparison JSON was not regenerated after the Phase A fix.**
`e52ef5e` changed `pipeline/phase_a_clean.py` and `docs/qaqc/tool-comparison.md` ("The table above was re-run after that fix: unchanged") but not `tool-comparison.json`. The raw numbers that back the "candidate wins" verdict are from before the fix, so the "unchanged" statement has no artefact. Also noted: both tools keep the well-known Simplified hallucination 「請不吝點讚 订阅 转发 打赏支持明镜与点点栏目」 (genai-meetup-1 `kept_low_examples`), so "hallucination retention did not rise" is true only as a delta; neither tool removes it. Metric "false drop" is a 4-gram test against the published text, which cannot score 1–2-character cues (md states this limitation, to its credit).

**B5 (low) — Two "field-proven upstream" tools are not in study's history.**
`scripts/lang/en/zh_parts_check.py` and `scripts/lang/en/srt_translate_zhtw.py` are untracked files in study's working tree (`git cat-file -e bdaca2b:…` fails for both) and are added as new files in this branch. "Byte-identical to study" holds only against that uncommitted working tree; they are not part of the lineage commit, and `zh_parts_check` was exercised on one session (AS1569) in the comparison. `docs/upstream.sha1` hashes all 21 as equally "upstream".

**B6 (low) — "Tamper-evident" is weaker than the wording.**
README §12 calls it "改不掉的紀錄". `pipeline/common.py:_entry_hash` has no secret or external anchor, `actor` is whatever `--actor` / `GSN_ACTOR` says (`gsn.py:106`, default "human-or-shell"), and `.gsn/` snapshots and the ledger live in the same directory. Anyone who edits a product, its snapshot and recomputes the chain passes A0/A4/A6. It catches accidental and casual edits (tests 2–4 prove that), not a deliberate rewrite. The statement should say so.

**B7 (med, S8) — Gate gaps a bad output could pass.**
(a) `gates.core()` removes `#` marks but keeps heading text, and `wordcount.py` counts it, so inserted headings count toward the 95–105 % band (the example's 1.024 is partly headings, stated in `orchestrator_log.md`). (b) `ngram_retention` is a set test of 4-grams at ≥ 0.90: up to 10 % of the speaker's content may vanish and order is not checked; zero omission rests on the ratio band alone, which headings can offset. (c) Phase A E4 (`>= 90 %`) is `warn`, not fail. (d) p4/p5 prove source lines are untouched but accept any text inside `>` blocks, so a stance block can still carry invented claims (S10 class; admitted in `eval-effort.md` conclusion 3). (e) The example's p3-punct/p3-hooks report 126 paragraphs vs 104 real ones (orchestrator F4). None of these was exploited in the examples; they are the places to harden.

**B8 (low) — Cross-CLI and Groq-via-gsn paths unverified.**
`pipeline/headless.py:41-56` builds command lines for gemini, codex, copilot and agy; every eval and the example used `claude` only, and `eval-effort.md` has no non-Claude row. README §5 table and §6 present all five as working; only `docs/agents.md` states "only measured assignments are marked live". README says `--model` values are illustrative, but not that the other four CLIs were never run.

**B9 (med) — Test and run coverage holes.**
All tests and the example use `--from-srt` (tests/test_pipeline.py:`gsn("new","--from-srt",…)`; ledger seq 2 `how: imported SRT`). The `gsn.py new <audio>` → `transcribe()` rename path (`gsn.py:~290`) was never executed end-to-end; the comparison harness called the upstream Groq scripts directly. No tests cover the p4/p5/p6 gates (only `inserted_only` unit), wordcount band failure, `loop_log`/`improve`, `headless`, or `doctor`. 18 tests that all pass are real (the tamper tests do fail when the code is wrong: they assert FAIL lines), but the surface is the Phase 3 chain only.

**B10 (low) — Publishing and history hygiene.**
(a) GitHub `shuotao/study` has `main` = `e52ef5e`, no `cli-edition` ref; docs say "cli-edition branch"; local `origin` is `GENAI.git`. (b) The published history carries all of study (web pages, admin code, `firebase-config.js` with a public `AIza…` web key, flagged by its own comment as non-secret). Not a leak, but it is published. (c) Pre-commit hook not active here (`gsn.py doctor`: FAIL "pre-commit secret scan hook"; `git config core.hooksPath` unset), so protection depends on running `doctor --fix`. (d) `secret_scan.py` `ALLOW` names `tests/test_secret_scan.py`, which does not exist; scan only covers the working tree, not history.

**B11 (low, S-class: role fidelity) — Roles as built differ from the spec, and the judge is not independent.**
BUILD_LOG: the repo was orchestrated and implemented by Opus 5.5, Fable only ran the example. In the example every Phase 3–5 stage was an Opus subagent and the p6 `done`, K confirmation, `speakers.json` and `meta.json` decisions were made by the orchestrator in place of the human (all disclosed in `orchestrator_log.md`; the example observer rated it WITH NOTES). In the effort eval the blind judge is Opus and ranks `opus·low` first (n = 1, one judge); the doc labels its conclusions hypotheses, which is the right wording.

**B12 (low) — Small inconsistencies.**
CLAUDE.md says observer codes S1–S9; `prompts/observer.md` defines S10. The example observer's stage table "rounds (gate fails)" mixes attempts with failures (see B2). `trigger-results.json` is a single-model, single-description run (Sonnet, effort null); the negative cases are easy, so 18/18 shows little about borderline triggers.

Checked and fine: eval table vs json; tool-comparison table vs json (same pre-fix run); word-count arithmetic (6588 / 6748 / 6795 / 1.031 match `wordcount_report.json`); audit rows A0–A9 all pass on the example; upstream hash list; no media, `.env` or session files tracked; no email addresses in HEAD; pointer files; docs-sync test; phase prompts exist for every stage.

## Recommendations
1. Put the example evidence in the repo: commit a trimmed `docs/qaqc/example-run.md` plus copies of `audit_report.json`, `wordcount_report.json`, `observer_report.md` (no raw talk text beyond the existing fixture), or remove the README/BUILD_LOG claims (B1).
2. Make `gsn.py check` append a `check-fail` ledger entry and `loop_log` call; have audit A8 count both (B2).
3. Re-run `pipeline/candidates/compare.py` on the current `phase_a_clean.py` and commit the new JSON (B4); update BUILD_LOG and commit it (B3).
4. Add to the gates: heading text excluded from the ratio, ordered retention (or a per-paragraph 4-gram check), Phase A E4 as a fail below a stated floor, and a banned-claim check for `>` blocks (B7).
5. Run one real `gsn.py new <audio>` (a 2-minute clip) and one headless stage on a non-Claude CLI, or mark those paths "untested" in README §5–6 (B8, B9); add tests for p4/p5 gates and a wordcount failure.
6. Soften "改不掉" to "改了會被發現（除非整條重寫）", or anchor the chain head outside the session directory (B6).
7. State in README §12 that `zh_parts_check.py` and `srt_translate_zhtw.py` are from study's uncommitted working tree and should be committed upstream (B5); align the branch name wording with what is on GitHub (B10).
8. Run `gsn.py doctor --fix` before the next commit so the secret hook is active; fix the stale `ALLOW` entry.
