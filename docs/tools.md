# Tool registry

The one list of every tool. `tests/test_repo_hygiene.py` fails when a tool file is missing here.
Two kinds, kept apart on purpose:

- **Upstream (study, unchanged)** — field-proven across the study sessions. Byte-identical to study commit 810fa13
  (`docs/upstream.sha1`, checked by the test suite; `zh_parts_check.py` and `srt_translate_zhtw.py` are not committed in
  study yet and match its working tree). Fix them upstream, then sync here.
- **New in the CLI edition** — the layer study did not have: one entry point, gates, ledger, audit, headless,
  word-count chain, setup. Every new tool that *replaces* an upstream one is a candidate upgrade and must win a
  head-to-head comparison first (`docs/qaqc/tool-comparison.md`).

## Upstream tools (study, unchanged)

| Tool | Phase | Purpose |
|---|---|---|
| `.claude/skills/good-student-notes/scripts/groq_transcribe.py` | 1 | Groq Whisper large-v3, Chinese; FFmpeg chunks, key rotation, resumable chunk cache, `GROQ_NO_PROMPT`, `GROQ_CHUNK_SECONDS` |
| `scripts/lang/en/groq_transcribe_en.py` | 1 | same for English |
| `SRT/qaqc_srt.py` | 1 | Phase A (default): hallucination prefixes, garbled cues with speech exemptions, typo dictionary; timecodes untouched |
| `scripts/s2t_normalize.py` | 1 | Simplified-drift → Taiwan Traditional glyphs (OpenCC s2tw), refuses transcript.srt |
| `scripts/lang/en/srt_zhtw.py` | 2 | prep / assemble timeline-locked EN→zh-TW, byte-identical timecode proof |
| `scripts/lang/en/zh_parts_check.py` | 2 | translation gate C1–C7 |
| `scripts/lang/en/srt_translate_zhtw.py` | 2 | optional batch translator through headless Antigravity (`agy -p`) |
| `scripts/normalize_punctuation.py` | 3C | full-width punctuation; `--check` = residual count |
| `scripts/para_len_check.py` | 3B | paragraph length 60–120 CJK, shorter rather than longer |
| `scripts/phase_d_check.py` | 3D | insert-only proof: 1:1 paragraphs, subsequence, growth cap |
| `scripts/dialogue_check.py` | 3 | panels: speaker attribution and turn order |
| `scripts/pipeline_logger.py` | all | log → check → improvement queue (the iteration loop) |
| `scripts/tests/test_pipeline_logger.py` | — | its tests |
| `scripts/tests/test_qaqc_srt.py` | 1 | tests for the R1.2 exemptions and short replies (added upstream 2026-10-22) |
| `dict/load.py` | 1 | dictionary loader (+ `dict/*.json` data) |

## New in the CLI edition

| Tool | Purpose |
|---|---|
| `gsn.py` | entry point: doctor, new, status, next, check, done, audit, wordcount, improve, headless, resume |
| `pipeline/__init__.py` | package marker |
| `pipeline/common.py` | stage graph, SRT parse, counting rule, hash-chained ledger, markers |
| `pipeline/md_parse.py` | paragraph model shared by Phase 3 and the matrix (extracted from study `md_to_html.parse`) |
| `pipeline/gates.py` | one gate per stage, calling the upstream tools where they exist |
| `pipeline/wordcount.py` | word-count QAQC chain: original cues → every stage, same basis, bands per stage |
| `pipeline/audit.py` | A0–A9 after-the-fact proof from ledger, snapshots, frozen outputs, word-count chain |
| `pipeline/headless.py` | drive pending stages through claude / gemini / codex / copilot / agy, 3-round breaker |
| `pipeline/init.py` | environment doctor behind `/init` |
| `pipeline/secret_scan.py` | pre-commit hook: keys, .env, media, session products |
| `pipeline/eval_effort.py` | model × effort eval for judgment stages |
| `pipeline/candidates/compare.py` | head-to-head harness: candidate vs upstream on real study sessions |
| `pipeline/candidates/phase_a_clean.py` | superseded candidate: won round 1, tied/lost after the upstream fix (round 2); `--phase-a candidate` |
| `pipeline/candidates/transcribe_groq.py` | rejected candidate (kept to re-run the comparison; never called) |
| `pipeline/candidates/translate_srt.py` | rejected candidate (kept to re-run the comparison; never called) |
| `pipeline/candidates/__init__.py` | package marker |

## Phase 6 — `matrix/tools/` (from N; verbatim import + one layout commit; spec `matrix/SPEC.md`)

| Tool | Purpose |
|---|---|
| `matrix/tools/n.py` | matrix entry: init, build, check, status, links, vault, all, qa |
| `matrix/tools/anchor_source.py` | anchor cleaned.md paragraphs as `pNNNN` (read-only) |
| `matrix/tools/anchor_aux.py` | anchor the speaker's own handout as `hNNN` (IV only) |
| `matrix/tools/render_ii_iii.py` | render II and III; `--verify` = verbatim check |
| `matrix/tools/render_i.py` | render I key-point cards |
| `matrix/tools/render_diagram.py` | render I diagrams (SVG, dagre layout) |
| `matrix/tools/dagre_layout.cjs` | node helper for dagre |
| `matrix/tools/render_iv.py` | render IV cross-session page |
| `matrix/tools/render_hub.py` | render the 2×2 hub |
| `matrix/tools/ui.py` | shared page components |
| `matrix/tools/topics.py` | III deep-dive topics from iv.json |
| `matrix/tools/vault.py` | Obsidian export |
| `matrix/tools/link_candidates.py` | cross-session candidates (TF-IDF, same genealogy) |
| `matrix/tools/links_merge.py` | worker batches in, judged batches merged |
| `matrix/tools/links_check.py` | gate L0–L7 |
| `matrix/tools/k_draft_check.py` | gate D1–D5 for K.json |
| `matrix/tools/k_check.py` | gate for I/IV pages |
| `matrix/tools/iii_check.py` | gate T1–T7 for III |
| `matrix/tools/iv_check.py` | gate J1–J6 for iv.json |
| `matrix/tools/provenance_check.py` | claims provenance |
| `matrix/tools/diagram_check.py` | gate D1–D5 for diagrams |
| `matrix/tools/views_check.py` | source unchanged since anchoring; anchors exist |
| `matrix/tools/ui_check.py` | font floor, how-to-read box, no overflow |
| `matrix/tools/quiz_aggregate.py` | comprehension quiz gate |
| `matrix/tools/n_lint.py` | resume check from STATE.json |
| `matrix/tools/jargon_common.txt` | jargon list for k_check |
