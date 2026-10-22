# Worker prompt: quadrant I entry page i.json v3 (Sonnet)

Read first:
- `docs/SPEC.md` §13.1 (including W4a, W5, W5a, W9), §13.2
- `prompts/_provenance.md` (the per-unit provenance procedure; this prompt's rules must not be looser than it)
- `runs/<run>/K.json`: 7 key points. `point` and `anchors` are the basis; `i_angle` is only a "hint for the angle of entry", **not a quotation, and not guaranteed to be something the source says** (see "Titles and openings" below).
- `runs/<run>/source.anchors.json`, and the `cleaned.md` it points to

**Language: write all user-facing text (title, headline, paras, gloss) in Traditional Chinese (zh-TW), full-width punctuation. This prompt is in English only because it is for AI; the Chinese strings quoted below are literal required wording or source examples and stay in Chinese.**

Reader: someone encountering this topic for the first time, e.g. an architecture student or a BIM practitioner who has just started using AI. They do not know programming and do not recognize the speaker's terms. They have not yet decided whether to spend time reading the full content.
Goal: after 3 minutes of reading, they know what this talk is about, why it matters to them, and want to click through to the source.

Produce `runs/<run>/i.json` (**write only content data, not HTML**). Layout, lists, font sizes, and the footer routing are all produced by
`tools/render_i.py` + `tools/ui.py`, sharing the same components as II/III/IV (SPEC §6). After writing, run `python3 tools/n.py build runs/<run>`.

## 一、Data format

```json
{"title": "這場在講：…一句話（依 §二 處理術語）",
 "items": [{"k": "K1", "headline": "白話標題（規則見 §三）", "anchors": ["p0024", "…"],
            "paras": [{"text": "為什麼在意，一句", "gloss": {"term": "LLM", "text": "LLM＝…", "after": "（選填）補述接在哪段字之後"}}],
            "more": ["p0025"]}]}
```
(Gloss of the placeholders: title = "This talk is about: ... one sentence (terms handled per §二)"; headline = "plain-language headline (rules in §三)"; text = "why they should care, one sentence"; after = "(optional) after which text the supplementary note attaches". The 「這場在講：」 prefix of title is required wording.)
- items follow the order K1-K7; `anchors` ⊆ that point's anchors in K.json.
- Each card has 2-3 paras, each sentence <= 35 Chinese characters (supplementary notes are not counted in these 35, but are counted in the page-wide 1,200 characters).
- `gloss` is the supplementary note of ladder step 2 (§二); at most 1 per card, at most 7 per page; `text` does not include the outer frame 「〔補述：」 (supplement:), the tool adds it.
- `more`: 1-2 "read the source" link paragraphs (selection in §五); the tool uses the title of the section the paragraph belongs to as the link text.
- Do not write page counts, times, or "this page has N key points": the tool computes them.

## 二、Handling terms (new in this version; this was the main cause of v1's failure)

Term = a word an ordinary architecture student would not understand. Criterion: if, after removing the explanation, a person who has never touched programming would ask "what is that", it is a term. Common ones: token, SDD, .md, API, 代理 (agent), 模型 (model; only when it means an AI/language model, a CAD or building model is ordinary vocabulary and is not a term, see jargon.txt scope below), 外掛 (plugin), 宿主程式 (host program), 穩定層／可替換層 (stable layer / replaceable layer), 機率性／確定性 (probabilistic / deterministic), 架構 (architecture), 提示 (prompt), harness, MCP. This list is only examples; apply the same criterion to other terms.

**Keep the speaker's words (SPEC §13.1 W5), but each term, the first time it appears on each card, must come with an explanation.** Each card is self-sufficient; do not assume the reader has seen the previous card. Choose from the ladder below, from top to bottom, the first one you can do:

**Ladder step 1: explain it using the source's own plain language.** First search the whole `cleaned.md` for the speaker's or the edited transcript's explanation of this word (use search, not memory). If found, write it straight into the sentence in the form 「術語（原文的說明）」 (term (the source's explanation)); the explanation must be a contiguous substring of the source or a paraphrase hugging the source. Such an explanation is a **source claim**: attach the anchor to the paragraph where the explanation lives and handle it under the general rules of `_provenance.md`; it is not a supplementary note. Known examples for this session (to show the method; for another session, search again; do not copy):
- token -> 「單字、數字或概念」 (a word, number, or concept) (p0021)
- SDD -> 「規格驅動開發」 (spec-driven development) 「把想法組織起來、寫成文件」 (organize ideas and write them into documents) (p0065, p0066)
- .md file -> 「本質上是文字檔」 (essentially a text file) (p0066)
- 代理 (agent) -> 「ChatGPT、Claude Code、Codex 與 Copilot 這類使用語言模型的東西」 (things like ChatGPT, Claude Code, Codex and Copilot that use a language model) (p0017, the speaker explains by example)
- 穩定層／可替換層 -> put in parentheses what the speaker lists in the same paragraph: 「穩定層（規格、架構、工具、測試）」 (stable layer (specs, architecture, tools, tests)) 「可替換層（代理與模型，會不斷演進）」 (replaceable layer (agents and models, which keep evolving)) (p0043)
- 宿主程式 (host program) -> elsewhere the speaker gives an example with 「兩個執行宿主：AutoCAD 和 Revit」 (two execution hosts: AutoCAD and Revit); you may write 「實際宿主（AutoCAD、Revit 本身）」 (actual host (AutoCAD, Revit itself)), anchor attached to that paragraph. If you cannot find that paragraph, use ladder step 2 or 3 instead.
- 機率性／確定性 (probabilistic / deterministic) -> do not use these two words. Rewrite what the speaker said in p0022: 「每個答案各有機率，模型挑最可能的」 (each answer has its own probability; the model picks the most likely).

**Ladder step 2: supplementary note (use only when the source has no explanation).** Fixed format:
`<span class="supp" data-term="外掛">〔補述：外掛＝加裝在 Revit 或 AutoCAD 裡、擴充它功能的程式〕</span>`
(Gloss: 補述 = "supplement"; the example reads "plugin = a program installed inside Revit or AutoCAD that extends its functions". The literal frame 〔補述：…〕 is required wording matched by tools.)
All the limits on supplementary notes must be obeyed:
1. It must begin with 「〔補述：」 and end with 「〕」, and use `class="supp"`, so readers and the checker tool can recognize it.
2. It may only be a dictionary-style explanation of "what this word generally means", <= 28 Chinese characters. It must not describe what the speaker did, said, or what this talk contains.
3. It must not contain numbers, years, version numbers, product capabilities, comparisons (「比…快」 "faster than..."), causality, or evaluation.
4. After removing the note, the claim of the whole sentence must remain completely unchanged. If the sentence is incomplete without it, you have hidden a claim inside the note; go back to ladder step 1 or step 3.
5. At most 1 supplementary note per card, at most 7 per page. The same term is explained only at its first appearance.
6. The note is attached to the sentence where the term appears; it does not stand alone as a sentence.

**Ladder step 3: do not use the word.** If steps 1 and 2 are both impossible (no explanation, note quota used up, or the explanation is too long), rewrite the whole sentence to say only the plain-language part of the source; if still impossible, delete the sentence and pick another point for which the source has a plain-language way of saying it. Expert details (API, versions, file names, conditions) belong to IV anyway; do not force them in with supplementary notes.

**Never satisfy the jargon gate by deleting the speaker's word.** If a term the speaker actually used (it appears in the card's anchor paragraphs or K point) is flagged, the only valid remedies are ladder step 1 or 2 (explain it), or step 3 when you rewrite the whole sentence in the source's plainer wording. Removing just that word, or swapping in your own synonym, changes the speaker's claim. If you believe the word is not a term in this session (e.g. 模型 meaning a CAD model), report `GATE DISPUTE` (see end of this prompt); the orchestrator adds it to the run's `jargon.txt` scope. Check after editing: every term the K point uses is still present on its card, or the card explains why it is absent.

**Term quota per card:** 0 unexplained terms in the title; at most 2 terms introduced on the whole card.

## 三、Titles and openings (new in this version)

The title, like every sentence, is a unit to be traced.
- **You must not use `i_angle` directly as the title.** `i_angle` may contain claims the source does not have. Method: first find, in the card's anchor paragraphs, the one sentence that best represents the point and copy it as the quote, then write the title in plain language. Every claim in the title must match the quote.
- The title must not contain causality, universal claims, or turns that the source does not state (「為什麼…」 "why...", 「反而…」 "on the contrary...", 「一定…」 "definitely...", 「每次…」 "every time..."), unless the source has the same word.
- Sentence 1 must speak in the reader's world, not in terms. Prefer the speaker's own analogies, because the readers of this page mostly study architecture: p0057-p0062's grid lines, floors, and client needs corresponding to the software's business requirements, design intent corresponding to the spec, construction corresponding to implementation, and foundations and heavy rework. If the source of other cards also has an everyday or architectural way of saying it, use it.
- An analogy may only use correspondences the speaker has made; do not add correspondences yourself (e.g. do not say "a spec is a construction drawing" on your own). If a card's anchors contain no analogy, open directly with the plain-language explanation of ladder step 1; do not force one.

## 四、Provenance procedure (follow `_provenance.md`, plus two rules)

Before writing the product, build the provenance table. List one row for **every unit**: the title, the header h1, each sentence, each supplementary note. Columns: unit text | each thing it depends on | anchor | quote | qualifiers | whether the qualifier is kept.
1. **Anchor completeness.** After writing each unit, search each of its nouns and verbs in the labeled paragraph; if you cannot find one, search 3 paragraphs before and after; if found, add that paragraph to the unit's anchors. **A card's `data-anchors` = the union of the anchors of all its units, and must be ⊆ that K's anchor set.** Do not attach an anchor merely because "this paragraph is probably relevant", and do not omit the literal source.
2. **Compression must not drop the subject or object.** When a sentence exceeds 35 characters, solve it by splitting the sentence, not by deleting the object or subject of the action. E.g. 「要求它更新 SDD 堆疊」 (ask it to update the SDD stack) must not be shortened to 「要求它更新」 (ask it to update). If it cannot be split, use ladder step 3.

Also, **keep the speaker's words as they are** (e.g. do not write 「差」 (poor) as 「含糊」 (vague), do not write 「規劃」 (plan) as 「設計」 (design)). Attach an explanation per §二 only when the word is a term; do not replace words that are already plain in the source.

## 五、Link selection

`<a href="ii.html#pNNNN">`: pick 1-2 paragraphs from that card's K anchors; **the paragraph must be understandable when read alone**:
- First read the candidate paragraph's first sentence. If it starts with a connective or a pronoun reference (它、這、同樣、一旦、邏輯是一樣的、如上所述: it, this, likewise, once, the logic is the same, as above), do not pick it.
- Prefer the paragraph where "the concept is first explained", and the paragraph containing the source explanation you used in §二 (e.g. the token explanation paragraph).
- If the candidate paragraph's premise lies in an earlier paragraph, pick that earlier paragraph instead (as long as it is inside the K anchor set). If the K anchors have no suitable entry paragraph, say so in your reply; do not force a pick.

## 六、Content selection (new in this version)

This is an entry page, not a shrunken full text.
- Statements only experts understand, which require understanding software architecture first, belong to IV and are not put here. Test: if a sentence needs two or more supplementary notes to be understood, do not include it.
- The 3 sentences of each card must convey one "reason the reader would care", not three unrelated facts.
- For points about boundaries and limits like K6 and K7, use the source's plainest wording closest to ordinary work experience (e.g. 「結果取決於你的經驗」 "the result depends on your experience", 「人要自己做決定、自己測試」 "people must decide and test for themselves"); do not open with words like API or host program.

## 七、Self-check

1. Run `cd ~/Desktop/N && python3 tools/k_check.py runs/<run>`. If iv.html does not exist yet (it is built from links/links.json), ignore the 'iv.html missing' line and fix everything about i.html.
2. Against the provenance table, answer the five questions of `_provenance.md` for each unit.
3. Term scan: after `n.py build`, read i.html through from the start; for every term, at its first appearance within its card, is there a ladder step 1 explanation or a ladder step 2 note beside it? Are the titles term-free? Is there at most 1 note per card and at most 7 per page?
4. Remove all `class="supp"` spans and read again: does each sentence's claim remain unchanged?
5. Open `verify/i.png` to check the layout and confirm the notes can be told apart from the body at a glance.

Write only `i.json`. Reply with only:
- Body character count (including notes); the number of notes and the term of each.
- Each card's `data-anchors`.
- The quotes of the "title" rows of the provenance table (for the verifier's spot checks).
- If any card could not be completed because the K anchors were insufficient, say which card and what is missing.
- Self-check results.
~~~~

## 八、Attribution tone (v2.1, lesson from Shen Boyang session persona neutrality score 3, 2026-10-12)
- The speaker's claims, plans, promises, and evaluations are always attributed in the third person: 「他提出／他認為／他希望／他說」 (he proposes / he believes / he hopes / he says). Never use the speaker's first person (「我們提出」 "we propose", 「我們認為」 "we believe") as the page's narration. Otherwise the reader takes the speaker's claims as this page's position, which reads like promotion especially for political platforms, product launches, and sales talks.
- What the speaker calls a hope, goal, or intention must not be written as done or inevitable.
- Do not add views from outside the speaker, and do not add assessments of "whether it can be done"; those belong to IV's "worth verifying". I is responsible only for making clear whose claim it is.

## When a gate seems wrong (escalate; never bend the content) — Observer 2026-10-13
- A gate failure is a signal, not an order to change the text. Before editing, decide which it is: (a) the product really violates the rule -> fix the product by the rule's own remedy (e.g. add the gloss the jargon gate asks for); (b) the gate is wrong or too blunt for this session (false positive, wrong scope, rule contradicts another rule).
- If (b), **do not make the gate pass by changing what the speaker said**: do not delete or replace the speaker's word, drop a unit, loosen an anchor, split one claim to dodge a length cap, or reword into something the source does not say. A product that passes by being less faithful is worse than a red gate.
- Instead: leave the content faithful, stop, and report in your reply under a heading `GATE DISPUTE`: gate id + exact failure line, the source paragraph id and quote it conflicts with, why you think the gate is wrong, and the smallest change (to a tool or a per-run file such as `jargon.txt`) that would fix it. The orchestrator fixes the tool or decides; you do not.
- If you did make any workaround to get green, say so explicitly under `WORKAROUNDS` (what you changed and why). Silence about a workaround is a defect.
- Never "fix" a count, id, or status field by hand to match the checker; counts are derived by tools.
