# Quiz author prompt v1 (Opus): I-page acceptance quiz, `quiz.json`

Spec: `matrix/SPEC.md` §13.7. Purpose: measure whether the I page (`i.html`) lets a first-time reader actually understand the talk. A comprehension task replaces the old "difficult sentence count". You write the quiz; a persona (`matrix/prompts/quiz_taker.md`) takes it; a grader (`matrix/prompts/quiz_grader.md`) grades it; `matrix/tools/quiz_aggregate.py` aggregates it.

Write all user-facing text (`question`, `key`, `must_include`) in Traditional Chinese (zh-TW), full-width punctuation. This prompt is in English because it is for AI.

## Inputs (read these only)
- `matrix/runs/<run>/K.json` (the 5-7 key points and their anchors)
- `matrix/runs/<run>/source.anchors.json` (the source, paragraph by paragraph)
- `matrix/runs/<run>/i.json` and `matrix/runs/<run>/i.html` (what the persona will see; to confirm the quiz is answerable from the I page)

## What to write
Write `matrix/runs/<run>/quiz.json` and `matrix/runs/<run>/quiz_questions.json`.

`quiz.json` has exactly 4 items: 3 comprehension questions (`q1`, `q2`, `q3`) and 1 navigation task (`nav1`):

```json
{"version": 1,
 "items": [
  {"id": "q1", "type": "comprehension", "question": "...", "key": "...",
   "must_include": ["...", "..."], "anchors": ["p0024", "p0025"], "K": "K1"},
  {"id": "q2", "type": "comprehension", "...": "..."},
  {"id": "q3", "type": "comprehension", "...": "..."},
  {"id": "nav1", "type": "navigation", "question": "...", "key": "...",
   "must_include": ["..."], "anchors": ["p0034", "p0040"], "K": "K2",
   "acceptable_targets": ["ii.html#p0034", "ii.html#p0040"]}
 ]}
```

`quiz_questions.json` is the same questions with **no answers**, the only file the persona may read besides `i.html`:

```json
[{"id": "q1", "question": "..."}, {"id": "q2", "question": "..."}, {"id": "q3", "question": "..."}, {"id": "nav1", "question": "..."}]
```

## Rules for the 3 comprehension questions
1. Each question tests one different K (three different K), chosen so that together they cover the backbone of the talk. Set `K` to that key point.
2. Each question must be answerable **from the I page alone** (the card text and diagrams in `i.html`). Do not ask for anything that exists only in the full source, and do not ask for the timeline, budget, or first step that the source does not state (per SPEC §13.7: what the source lacks cannot be supplied by the I page).
3. Ask for understanding, not recall of a word: "why", "what is it reminding you of", "what is the order and what to do on error", not "what is the name of X". Do not make the answer a single term.
4. Use the speaker's words and analogies (SPEC §13.1 W5). Do not add claims, causality, universal statements, or opinions that the source does not have. Speaker claims are attributed to the speaker in the question wording if needed.
5. `key`: a 1-2 sentence model answer drawn from the source (not from your external knowledge).
6. `must_include`: 2-4 short points (each a short Chinese phrase). A correct answer must contain the idea of every point, though not necessarily the same words. Do not put more points than the question really asks for.
7. `anchors`: 2-6 paragraph ids in `source.anchors.json` that contain the key; they must exist, and each point of `must_include` must be supported by them. Verify by searching the source text; do not rely on memory.
8. Speaker attribution: if the key comes from an audience paragraph (see `speakers.json` if present), the question must not present it as the speaker's claim.

## Rules for the navigation task (`nav1`)
1. It asks where to click on the I page to read the relevant source paragraph, e.g. "if you want to know X, click the link on which card to read the source?". Pick a K different from or equal to the comprehension ones, but its answer must be an actual `more` link on a card of `i.html`.
2. `acceptable_targets`: every `ii.html#pNNNN` target that a reasonable reader could choose and that really contains the information (the card's `more` links, plus any other paragraph that explains it first). Each must be an anchor that exists.
3. **Mechanical grading warning.** `matrix/tools/quiz_aggregate.py` takes every `pNNNN` string found anywhere inside the `nav1` item (question, key, must_include, anchors, acceptable_targets, all of it) as an acceptable target. Therefore: put in the `nav1` item **only** paragraph ids that are truly acceptable, and never mention an unacceptable paragraph id in any of its fields. The item id must start with `n` (the aggregator treats ids starting with `n` or `nav` as navigation items).
4. `key` describes in words which card and which link to use (e.g. "click `想深入 -> 讀原文這段` on the card titled ..."); `must_include` states the card to find and the link to click.

## Self-check (do before finishing)
1. Every `anchors` and `acceptable_targets` id exists in `source.anchors.json`.
2. For each comprehension question, search `i.html` to confirm each `must_include` point is visibly there (so the quiz measures the I page, not the reader's luck). If a point is not on the I page, rewrite the question or the point.
3. `quiz_questions.json` contains no key, no must_include, no anchors, no K.
4. Both files parse as JSON (UTF-8).

Write only `quiz.json` and `quiz_questions.json`. Reply with: the 4 questions (one line each), the K each tests, and any must_include point you could not locate on the I page.
