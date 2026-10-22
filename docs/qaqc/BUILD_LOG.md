# Build log — how this repository was made

Purpose: let a reviewer (human or the observer agent) check the build for shortcuts. Each entry: what was
done, by which role, with which evidence. Times are 2026-10-22 (Asia/Taipei).

## Roles in this build

| Role | Who | Note |
|---|---|---|
| Requester / final judgment | the author (TAO) | stated goals; "human out of the loop until the repo is done"; approved the talk text as fixture |
| Orchestrator + implementer of the repo code | Claude Code main session, **Opus 5.5** | the session was started on Opus, so the orchestrator seat that the design gives to Fable was held by Opus for the code build; Fable 5.1 was used as orchestrator for the end-to-end example run (B9) and appears in the effort eval |
| Implementers in the eval | headless `claude -p` processes (Haiku / Sonnet / Opus / Fable at various efforts) | driven by `pipeline/headless.py` |
| Observer | **Sonnet 5.5**, fresh context | `docs/qaqc/observer-build.md` (this build) and the example session report |

## Sources (read-only; nothing was written back)

- `~/Desktop/study` — CLI pipeline (session.py, groq_transcribe.py, qaqc_srt.py, normalize_punctuation.py,
  phase_d_check.py, para_len_check.py, srt_zhtw.py, zh_parts_check.py, qaqc_core_rules.md, gotchas.md)
- `~/Desktop/N` — matrix tools, prompts, SPEC.md
- `~/Desktop/context` — talk transcript 「說話與聽話」 (fixture + phase definitions)

## Steps

| # | Step | Evidence |
|---|---|---|
| B1 | First attempt: a fresh repo at `~/Desktop/good-student-notes` (pushed once). **Superseded at the author's request** ("branch from the original project"): this repo is now the `cli-edition` branch of study (git worktree `~/Desktop/study-cli`), force-pushed over that first commit. study's own branches and GENAI remote untouched. | `git log` on GitHub: study history + 5 cli-edition commits |
| B2 | Scope decision: CLI only. Dropped from study: Web studio, Firebase publishing, admin back-end, image notes, Gemini-API path (`--engine api`), language-specific batch scripts. Dropped from N: book publishing, Jev/TypeSafe prefilter (paid API), eval of links, legacy tools. | `docs/tools.md` |
| B3 | Matrix tools ported; path coupling to `~/Desktop/study` removed (`anchor_source.py` now imports `pipeline/md_parse.py`; images linked by relative path); `n.py qa` no longer checks the study repo; SPEC §1 and §11 rewritten. | `matrix/SPEC.md`, `matrix/tools/n.py` |
| B4 | Pipeline rewritten around one stage graph (`pipeline/common.py`), markers + `gsn.py done` + gates + hash-chained ledger + audit. New vs study: tamper-evident ledger, frozen output snapshots, chain continuity proof, 4-gram retention gate, line-subsequence proof for Phases 4–5, headless driver for 5 CLIs. | `pipeline/` |
| B5 | Transcription: language auto-detect by default and neutral prompt (study gotcha 6), prompt-echo scan (gotcha 7), resumable chunk cache (new), key rotation (kept). | `pipeline/transcribe_groq.py`, `phase_a_clean.py` |
| B6 | Smoke run on the excerpt, all stages p1→p5 + matrix init, executed by the main session as implementer (session lived in the superseded first folder; not kept). | audit 44/44 at the time |
| B7 | Tests: end-to-end with a deterministic stand-in implementer + tamper tests (edit after done, ledger edit, transcript edit, summary, out-of-order, word change in punct stage) + hygiene (docs sync, pointer files, secrets, gitignore). | `python3 -m unittest discover tests` → 17 OK |
| B8 | Effort eval (Phase 3 chain × 6 configs, headless). | `docs/qaqc/eval-effort.md` |
| B9 | End-to-end example: full talk, Fable orchestrator (headless), Opus·low implementers for Phases 3–5, Sonnet matrix workers, Opus verifiers, Sonnet observer. | `docs/qaqc/example-run/` — audit 46/46, wordcount PASS, observer TRUSTWORTHY WITH NOTES |
| B11 | **Author correction: reuse the field-proven tools.** The first build had rewritten 6 study tools. Reverted: the study tools are now byte-identical (`docs/upstream.sha1`, test-locked); the 3 genuine rewrites were kept only as candidates and compared on real study sessions. | `docs/qaqc/tool-comparison.md` |
| B12 | **Author request: word-count QAQC** made explicit — `pipeline/wordcount.py` chain (E1/E4/95–105 %), `gsn.py wordcount`, audit A9. | `pipeline/wordcount.py` |
| B13 | **Author request: carry the iteration loop** — study `pipeline_logger.py` (unchanged) wired into every gate, plus the missing consumer (green re-run closes items; `gsn.py improve`). study's own eval had found 342 open items with no consumer. | `gsn.py loop_log` |
| B15 | Upstream fixes made in study and pushed to GENAI (main 5b3f5a7, live on Pages; feat 9ffc10a + 810fa13), synced here from 810fa13 (22 files in `docs/upstream.sha1`). Phase A comparison round 2: the fixed original ties or beats the candidate → default back to `SRT/qaqc_srt.py`, candidate superseded. | `docs/qaqc/tool-comparison.md` § Round 2 |
| B10 | Build observer (Sonnet, fresh context) reviewed this log against the repo: TRUSTWORTHY WITH NOTES, 0 high / 5 med / 7 low. | `docs/qaqc/observer-build.md` |
| B14 | Fixes from the build observer: real audio → Groq → gsn path run once (2-min clip, study key via a temporary gitignored .env link, removed after; 12 cues, all gates green) [B9]; `gsn.py check` failures now logged as repair rounds [B2]; phase-a comparison re-run [B4]; ledger-head hash in audit_report and honest hash-chain wording [B6]; S10 listed [B12]; example-run evidence committed [B1]. Not fixed, stated: gate gaps in B7 (headings count in the band; 4-gram retention is unordered), non-Claude CLIs not run headless [B8], Phase 2 never run on a new English session in this repo. | this commit |

## Defects found during the build (and how each was fixed)

| # | Found by | Defect | Fix |
|---|---|---|---|
| D1 | smoke run (gate output) | Phase A dropped the legitimate English term `domain knowledge` from a Chinese talk as "garbled" (inherited rule: CJK ratio < 25 %). A silent zero-omission loss. | short all-Latin cues (≤ 5 words) kept unless they match caption-service hallucination patterns; test `test_phase_a_keeps_terms_drops_caption_noise` |
| D2 | review while porting | the CJK hallucination prefix list contains `Thank you`, `sub`, `Subtitles` — applied to an English talk it would drop real sentences | prefix list applied to CJK sessions only; English sessions use pattern rules |
| D3 | smoke run | p5 gate compared "notes minus `>` blocks" with an input that itself had `>` blocks (enhanced.md) → false failure | replaced by `inserted_only()` line-subsequence proof for p4 and p5 (stricter and correct) |
| D4 | smoke run | p3-polish first attempt failed paragraph median (47 < 60): the gate worked; implementer (main session) merged paragraphs, round 2 passed | — (recorded as gate-fail round 1 in the ledger) |
| D5 | test run | ledger tamper test edited a field that was not present (actor differs inside Claude Code) → test proved nothing | tamper now edits the `create` action itself |
| D6 | review | Phase 2 "untranslated" rule only existed for a Chinese target | Han-characters-left rule for other targets |
| D7 | docs agent | risk that the project `/init` is shadowed by the built-in `/init` (which would rewrite CLAUDE.md) | per docs, a project skill replaces the built-in in a local terminal; implemented as `.claude/skills/init/` with `disable-model-invocation: true`; `gsn.py doctor` documented as fallback |
| D8 | trial headless run | Sonnet (low) put 「：」 colons and 「」 quotes into p3-polish — Phase C work done one stage early (bundling). Gates pass because punctuation is allowed in polish. | left as an observer finding class (S2) rather than a hard gate: a colon in polish is not wrong text, only wrong timing |

| D9 | author | 6 study tools rewritten instead of reused — a process error, not a code bug | B11: reverted to upstream; rewrites compared; 1 adopted (Phase A), 2 rejected |
| D10 | example run (Phase A) | 「我用 Google 的 Gemini Flash」 dropped as garble by BOTH study qaqc_srt.py and the first upgrade (CJK ratio rule vs code-switching) | upgrade keeps Chinese + real Latin words; test added; reported as an upstream issue |
| D11 | transcription comparison | the candidate transcriber (auto language + neutral prompt, a study gotcha's recommendation) lost 18 % content and fabricated a cue on a Chinese clip | candidate rejected; study's forced `zh` kept — evidence that the gotcha needs a caveat |
| D12 | translation comparison | candidate checker flagged correct 「核准」 as Simplified (12×) | candidate rejected; `zh_parts_check.py` kept |

## Known limitations (stated, not hidden)

- `matrix/tools/*.py` keep many Chinese comments and all Chinese UI strings from the source project; prompts and
  specs are English. Page text is zh-TW by design.
- The Phase 3 content gates are calibrated for Chinese; English talks get the ratio, retention and phrase gates
  but no paragraph-length gate.
- Phase 6 claim-count gates (≥ 20 claims, ≥ 4 number claims) assume a full-length talk; a short excerpt cannot
  produce III.
- Model names in README §6 examples are illustrative; use the names your CLI lists.
