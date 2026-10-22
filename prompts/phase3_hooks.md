# Stage p3-hooks — Phase D: hooks between sentences

Role: implementer. Rules: `prompts/rules.md` § R8.

## Do
Read the whole text first. At seams — topic change, start of an example, a callback to earlier content,
the next point in a list — insert a short **content-referring hook** from the seven kinds in § R8
(callback, framing, pivot, signpost, transition, restatement, closing). A hook must refer to something that
really exists in the text before/after it.

Insert only:
- between sentences or at the start of a paragraph; never inside a quote; never in a heading;
- never rewrite, reorder or delete a word of the existing text; paragraph count stays identical;
- panels: never move or merge a speaker's turn;
- total growth ≤ 12 % (a few hooks per section is typical, not one per sentence).
Use full-width punctuation in what you insert.

## Finish
```bash
python3 gsn.py check <slug> p3-hooks     # subsequence proof shows the first rewritten spot, if any
python3 gsn.py done  <slug> p3-hooks --actor <cli>:<model>
```
After this stage cleaned.md is the full text (quadrant II of the matrix). It is never edited again by a
later stage — Phases 4–6 write new files.
