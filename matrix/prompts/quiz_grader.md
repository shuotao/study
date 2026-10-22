# Quiz grader prompt v1 (Opus): grade the I-page comprehension answers

Spec: `matrix/SPEC.md` §13.7. You grade **comprehension questions only** (`q1`, `q2`, `q3`, i.e. items with `"type": "comprehension"`). **Do not grade the navigation task**: `matrix/tools/quiz_aggregate.py` grades it mechanically (the `href` in the answer must be inside the item's acceptable paragraph ids). Do not mention or judge navigation answers except to note in `scope` that they were not graded.

Write the `notes` text in English or Traditional Chinese (zh-TW, full-width punctuation); the grades themselves are booleans. This prompt is in English because it is for AI.

## Inputs (read these only)
- `matrix/runs/<run>/quiz.json` (questions, `key`, `must_include`, anchors)
- `matrix/runs/<run>/verify/quiz_ans_t1.json`, `quiz_ans_t2.json`, `quiz_ans_t3.json` (the persona's answers; use every `quiz_ans_t*.json` present)
- `matrix/runs/<run>/source.anchors.json` only if you need to resolve what a `must_include` point means. Do not use external knowledge.

## Grading rule
For each trial and each comprehension question, output `true` only if the answer **expresses the idea of every point in `must_include`** and **does not contradict `key`**. Otherwise `false`.
- Judge ideas, not wording. A paraphrase counts (for example "看不到你的東西" for "看不到模型" still counts as the same idea if it clearly says the AI cannot see what the user is working on; note such judgments in `notes`).
- Every `must_include` point is required. If one point is missing, the answer is `false`, even if the rest is good. Do not give partial credit and do not add points that are not in `must_include`.
- Extra true detail beyond the key is fine (do not penalize it). Extra detail that contradicts the key, or that states the opposite, makes it `false`.
- An answer that says "the page does not say" for a required point is missing that point.
- An answer that is only a restated term or a vague gesture ("要講清楚" without the reason when the point requires the reason) does not satisfy the point.
- Do not grade the persona's tone, length, or interest. Do not reward answers for sounding confident.
- Grade each trial independently; do not let other trials' answers influence you.

## Output
Write `matrix/runs/<run>/verify/quiz_grades.json`, exactly this shape (one object per trial present, with the trial key `t1`, `t2`, `t3` matching the file name; item ids are the comprehension ids only):

```json
{"t1": {"q1": true, "q2": true, "q3": false},
 "t2": {"q1": true, "q2": true, "q3": true},
 "t3": {"q1": true, "q2": false, "q3": true},
 "notes": {
   "t1.q3": "which must_include point is missing, or why a paraphrase counted",
   "scope": "Graded comprehension items q1-q3 only; nav1 not graded."}}
```

Rules for the file: UTF-8 JSON; values for the grades must be the booleans `true` or `false` (the aggregator counts only `true`); `notes` is free-form (keys such as `q1`, `t2.q2`, `scope`) and is not read by the aggregator; every false should have a note naming the missing point. Do not add other top-level keys.

After writing, run `python3 matrix/tools/quiz_aggregate.py matrix/runs/<run>` only if the dispatcher told you to. Otherwise the dispatcher runs it. Reply with only: for each trial the number of true grades, and the questions that were false.
