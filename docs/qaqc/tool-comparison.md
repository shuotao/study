# Tool comparison — rewritten tools vs the unchanged study tools

Rule (CLAUDE.md iron rule 10): a new tool that replaces a field-proven study tool becomes the default only after it
wins a head-to-head on real sessions. Corpus: study sessions (read-only; nothing written back). Ground truth for
Chinese talks = each session's published, human-proofed `cleaned.md`. Harness: `pipeline/candidates/compare.py`.
Raw numbers: `tool-comparison.json`. Run 2026-10-22.

## Verdicts

| Tool | Upstream (study) | Candidate (new) | Verdict |
|---|---|---|---|
| Phase A cleaner | `SRT/qaqc_srt.py` | `pipeline/phase_a_clean.py` | **candidate wins → default** (`--phase-a upstream` keeps the original available) |
| Groq transcription | `groq_transcribe.py` / `groq_transcribe_en.py` | `pipeline/candidates/transcribe_groq.py` | **upstream wins → kept**; candidate rejected |
| Phase 2 translation | `srt_zhtw.py` + `zh_parts_check.py` | `pipeline/candidates/translate_srt.py` | **upstream wins → kept**; candidate rejected |

## Phase A — 4 Chinese sessions + 1 English session

| Session | cues | upstream false drops | candidate false drops | candidate keeps extra | kept low-overlap (up / cand) |
|---|---|---|---|---|---|
| lightalking | 51 | 0 | 0 | 0 | 0 / 0 |
| genai-meetup-1 | 540 | 0 | 0 | 1 (「對。」) | 73 / 73 |
| genai-meetup-2 | 558 | **1** ("Writing is rewriting" — in the published text) | 0 | 7 (「了解」「是。」「對」, "Yeah of course", …) | 211 / 212 |
| songshan-xinyi | 803 | 0 | 0 | 43 (「好」「謝謝」「所以」「馬上」…) | 395 / 395 |
| AS1569 (English) | 397 | — | — | identical to study's EN path (396 kept) | — |

Second finding (from this repo's own example run, 2026-10-22): both versions first dropped the real sentence
「我用 Google 的 Gemini Flash」 as garble (3 Han in ~20 characters < 25 %). The upgrade now treats Chinese + real
Latin words as code-switching speech (noise symbols and foreign scripts are still dropped); upstream still drops it.
The table above was re-run after that fix: unchanged.

*False drop* = a dropped cue whose 4-grams are ≥ 50 % in the published text. The extra cues the candidate keeps are
one- or two-character replies: `qaqc_srt.py` drops every cue under 3 characters although its own docstring says
single-character replies are valid content. Keeping them is the zero-omission side; Phase 3 decides how they read.
Hallucination retention did not rise (low-overlap counts equal ±1). Limitation: 1–2-character cues have no
4-grams, so their correctness is argued from the rule, not measured.

## Transcription — 5-minute clips (600 s → 900 s), real Groq calls, both tools with the same key and context

| Clip | tool | cues | Han chars | precision vs published text | Simplified glyphs | notes |
|---|---|---|---|---|---|---|
| songshan-xinyi (zh) | upstream | 32 | **1201** | **0.917** | 2 | — |
| | candidate | 28 | 989 (−18 %) | 0.897 | 1 | fabricated cue 「中文字幕 沈伯洋 中文字幕 沈伯洋」 and a skipped passage after 「學校的老師，」 |
| AS1569 (en) | upstream | 28 | 540 words | — | — | — |
| | candidate | 42 | 540 words | — | — | same words (4-gram agreement 0.937), finer cue split |

The candidate's neutral prompt and auto language detection (a study gotcha recommendation) lost content on the
Chinese clip — in this test, study's forced `language=zh` + Chinese prompt was better. n = 1 clip per language;
enough to reject a replacement, not enough to tune further. The candidate's resumable chunk cache is worth porting
upstream on its own (a feature, not tested here).

## Translation — AS1569, the translations study actually published

Both assemble **byte-identical** subtitle files (396 cues, every timecode proven). The candidate's check raised
12 hard failures, all 「核准」 — correct Taiwan usage — flagged as Simplified: a false positive that would block a
correct translation. `zh_parts_check.py` handled it. The candidate's extra bilingual SRT is a convenience, not a
quality win. Upstream kept.

## What this changed in the repo

- `pipeline/phase_a_clean.py` is the default Phase A; `gsn.py new --phase-a upstream` runs `SRT/qaqc_srt.py`.
- Rejected candidates stay in `pipeline/candidates/` only so the comparison can be re-run; `gsn.py` never calls them.
- Upstream issues to report to study: (1) `qaqc_srt.py` drops < 3-char cues contrary to its docstring, drops
  short English quotes in Chinese talks and drops code-switching sentences (「我用 Google 的 Gemini Flash」); (2) port the chunk cache to `groq_transcribe.py`.
