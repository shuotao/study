# Rules (single source of truth for every judgment stage)

Lineage: this is the English edition of study's `prompts/qaqc_core_rules.md` (kept unchanged next to this file,
because the unchanged study tools cite it). Mapping: R1–R8 here = R1–R8 there, translated, with the CLI-only
parts kept (Web/image notes removed). Added here: R0 (iron rules gathered from study CLAUDE.md, incl. E1/E2/E4
and F1), R9 (Phase 2, from study srt_zhtw practice), R10 (Phase 6, from N). If the two ever disagree, this file
governs agents and the difference is a bug to report.

Audience: AI agents. Every stage prompt cites sections of this file (`§ R2.2` etc.); rules are never copied
into prompts or code. The gate that enforces each rule is named next to it — a rule without a gate is a
wish, so when you find one, report it.

Language: these rules are in English; everything you WRITE INTO A PRODUCT (cleaned.md, notes, cards) follows
the language of the talk. For Chinese talks that means Traditional Chinese (zh-TW, Taiwan glyphs) with
full-width punctuation.

---

## R0. Iron rules (all stages)

- **R0.1 Zero omission.** Keep every sentence the speaker said, except pure filler (呃、嗯、那個 used only as
  a filler). Never summarise, condense or paraphrase. Keep the first person; never write 「講者提到…」/
  "the speaker mentions…". *Gate: content 95–105 % + 4-gram retention ≥ 90 % (p3-polish), insert-only proofs (later stages).*
- **R0.2 Distinguish who is summarising (E2).** What is banned is *you* summarising. If the speaker
  themself says 「另一位講者提到…」, that is their own words and must stay. *Gate: only NEW summary phrases fail.*
- **R0.3 The SRT is evidence.** `transcript.srt` is never modified; timecodes are never shown to or produced
  by an LLM (R5). *Gate: audit A1, p2 byte-identical timecodes.*
- **R0.4 Supplements are added beside the text, never into it.** Terms (R4), stance blocks (R3) and any note
  live in `>` blocks; the speaker's text outside them stays byte-for-byte. *Gate: p4/p5 "unchanged outside > blocks".*
- **R0.5 Names come from authorities, not from ASR (F1).** Person / company / product names: use
  `context.txt`, the official agenda or the speaker's site. When unsure, leave the ASR form and list it
  in `sessions/<slug>/corrections.json` (`[{"heard": "…", "likely": "…", "why": "…"}]`) — do not guess.
  English talks: "Claude" is often heard as "Cloud"/"quad".
- **R0.6 One stage at a time.** Do only the stage on your task card; finish it with `gsn.py done`; never
  bundle stages, never delete markers / snapshots / ledger entries by hand. *Gate: audit A2–A6.*

## R1. Phase A — deterministic cleanup (tool: `SRT/qaqc_srt.py`, no LLM)

R1.1 drop hallucination cues (`dict/hallucination_prefixes.json`; English caption-service patterns in the
tool) · R1.2 drop garbled cues (`dict/qaqc_config.json`) · R1.3 typo dictionary (`dict/typo_dict*.json`) ·
R1.4 whitespace · R1.5 timecodes untouched.
Two layers of hallucination: layer 1 (above) is mechanical. Layer 2 — **fluent but invented sentences**
(e.g. "marine oil… coffee shop" during the opening music of a software talk) — only a reader can catch. In
Phase 2 list such cue ids in `p2/drops.json`; in Phase 3 do not carry them into cleaned.md and record each
one in `corrections.json` with `"why": "semantic hallucination"`.
Prompt echo: `phase_a_report.json.prompt_echo_suspects` non-empty → tell the user to re-run with `--no-prompt`.

## R2. Phase 3 / Phase B — polish into readable full text (`prompts/phase3_polish.md`)

### R2.1 Do
- Add punctuation (。，？！、) and a minimal number of plain connectives (然後、接著、也就是說、所以) where
  meaning breaks.
- Merge broken lines into paragraphs. **One semantic unit (a point, an example, a dialogue/quote) = one
  paragraph, target 60–120 CJK chars, shorter rather than longer.** Split on: topic shift, start of an
  example, start of dialogue/quote, a new point opened by 所以／但是／那. One paragraph = one line; blank line
  between paragraphs. *Gate: para_len_check (median 60–120, ≤ 20 % over 120, none over 240).*
- Make a pronoun concrete only when the referent is certain from context (它 → the actual noun); change
  nothing else in the sentence.
- Insert `##` / `###` headings between paragraphs; a heading never replaces text. One `#` title at most.
- **Panels (2+ speakers):** each turn is its own paragraph starting with plain `名字：`; paragraph order =
  ASR order; never regroup turns by topic; never merge two speakers; uncertain turns start with `〔待確認〕：`.

### R2.2 Never
Delete a sentence · condense · change meaning or tone · third-person narration · drop example details ·
touch timecodes · learn "deleting sentences" from a human's hand-edited final copy (that is the human's
privilege, not the pipeline's).

### R2.3 Quantities
Output content = 95–105 % of the input (Han characters for CJK talks, words otherwise; same counting
basis on both sides, images excluded). *Gate: p3-polish.*

## R3. Phase 5 — stance notes (`prompts/phase5_stance.md`)

Requires an identity (a profession, role or situation). Translate the talk's concepts into that stance's
analogies; every original paragraph stays (R0.4).
```markdown
> 📝 **學習摘要**
> - 核心主題：[one sentence]
> - [立場]視角的關鍵收穫：[2–3 points]

…original paragraphs…

> 🎯 **[立場]視角**
>
> - **類比**：[the concept in this stance's terms]
> - **應用**：[how it is used in this stance's work]
> - **連結**：[link to what this stance already knows]

…

> 💡 **核心洞察**
> [one paragraph in this stance's language]
```
Analogies must hold logically; no forced ones. Blank line above and below every block.

## R4. Phase 4 — term supplements (`prompts/phase4_terms.md`)

After the paragraph where a term FIRST appears, add once:
```markdown
> **專業知識補充：[term]**
>
> [2–4 plain sentences: definition, use, common misunderstanding or where to go next]
```
Original paragraphs untouched; one supplement per term; blank line above and below.
(English talks use `> **Term note: [term]**`.)

## R5. Timeline protection (architectural)

Anything that must keep timecodes goes through a structure-preserving tool: Python splits the SRT, the
LLM sees only a numbered text list, Python re-attaches the original timecodes and checks
`len(in) == len(out)` and byte-identical timecodes. Never read an SRT and write an SRT with an LLM.
*Tool + gate: `scripts/lang/en/srt_zhtw.py` + `zh_parts_check.py`.*

## R6. Products and stopping points

| Phase | Product | What it is |
|---|---|---|
| 1 | `transcript.srt`, `cleaned.srt` | timed raw transcript (evidence), mechanically cleaned |
| 2 | `transcript.zh-TW.srt` (second subtitle track next to `cleaned.srt`) | subtitles to study a recording in two languages |
| 3 | `cleaned.md` | **full text: no timecodes, merged, punctuated, readable — most users stop here** |
| 4 | `enhanced.md` | full text + term supplements |
| 5 | `notes_<identity>.md` | full text + stance notes (好學生筆記) |
| 6 | `matrix/runs/<slug>/` | Good-Student Matrix: II full text · I key cards · III deep reading · IV links |

Every product is a valid end point. Keep them all: each one is study material.

## R7. Phase 3 / Phase C — punctuation (`prompts/phase3_punct.md`)

R7.1 (tool) `scripts/normalize_punctuation.py --in-place` makes every mark in a Chinese line full-width
and protects decimals, versions, domains, file names, thousands, URLs, times, code and links.
R7.2 (judgment) put a full-width colon 「：」 after an **announcer** that names what comes next:

| Trigger | Pattern | Example |
|---|---|---|
| copula ending | …是／就是, 想法是, 原因是, 問題是, 解決方式 | 「我的想法就是，用 AI 來驗證」→「我的想法就是：用 AI 來驗證」 |
| speech verb introducing a quote | …說, …講說 | 「他就說，啊…」→「他就說：『啊…』」 |
| noun header introducing a list | 步驟、核心概念、這次的分享 | 「三個步驟：…」 |
| speaker label | 碩濤：、Claude 的回應是 | 「Claude 的回應是：『其實夠了啦』」 |
| example / restatement | 例如、換句話說 | 「例如：…」 |

Add 「」/『』 around quoted speech. Not a colon: ordinary commas between clauses, 所以／因為, enumeration 、.
Phase C may change punctuation ONLY. *Gate: residual half-width = 0; content characters identical; paragraph count identical.*

## R8. Phase 3 / Phase D — hooks (`prompts/phase3_hooks.md`)

Beyond bare connectives, insert **content-referring hooks** at seams (topic change, start of an example,
callback, next point):
1 callback (也因為上面的困擾、以剛剛…為例、就像前面講的) · 2 framing (會這樣拿出來討論的原因是、先講前提) ·
3 pivot (轉念一想、但從…的經驗來看) · 4 signpost (第二個是…、同時我還發現) · 5 transition (接下來要討論的是…) ·
6 restatement (也就是說、換句話說) · 7 closing (回到結論、以上就是…).
A hook must point at something real (the 「上面」 it names must exist) and must never add a claim, a cause or a link the speaker did not make (「會這樣拿出來討論的原因是：」 with no reason in the source is an invented cause). Fewer, accurate hooks beat many. **Insert only, between sentences;
never rewrite or delete; paragraph count 1:1; panels: never move a turn.** Growth ≤ 12 %.
*Gate: phase_d_check subsequence proof.*

## R9. Phase 2 — translation (`prompts/phase2_translate.md`)

Faithful, cue-by-cue (1:1), no merging text across cues, no added glosses in brackets, glossary terms
exactly as listed, Taiwan Traditional glyphs for zh-TW, official product terms kept. Semantic
hallucinations go to `drops.json`, not into the translation. *Gate: translate_srt.py check + assemble.*

## R10. Phase 6 — matrix

The matrix has its own spec: `matrix/SPEC.md` (§13 writing rules W1–W10, §9 gates) and worker prompts in
`matrix/prompts/`. The common principle: every unit cites a source paragraph `pNNNN`; LLMs write JSON
data only; tools render every page.
