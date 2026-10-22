# Stage p3-polish — Phase B: turn the cleaned transcript into readable full text

Role: implementer. Rules: `prompts/rules.md` § R0, § R2 (read them first).

## Input
- `sessions/<slug>/cleaned.md` — right now it is the Phase A plain text: one subtitle cue per line, no punctuation logic.
- `sessions/<slug>/context.txt` — names, companies, products, terms (authority for spelling, § R0.5).
- The snapshot `.gsn/p3-polish.base` is the same text; the gate compares against it. Never edit it.

## Do
1. Work through the text **in order, in chunks of 50–100 lines**. For each chunk: punctuate, add minimal
   connectives, merge lines into paragraphs of one semantic unit (60–120 CJK chars, shorter rather than
   longer), make certain pronouns concrete, fix names per context.txt.
2. Insert `##` section headings at real topic changes (and `###` sparingly). A heading is added *between*
   paragraphs; it never replaces a sentence. Put one `# <title>` line at the top.
3. Write the result back to `sessions/<slug>/cleaned.md`. For long talks write it in parts (append chunk by
   chunk) instead of one huge output — the content rule does not change, only how you write the file.
4. Corrections you were not sure about → `sessions/<slug>/corrections.json`.

## Self-check, then finish
```bash
python3 scripts/para_len_check.py sessions/<slug>/cleaned.md      # CJK talks
python3 gsn.py check <slug> p3-polish
python3 gsn.py done  <slug> p3-polish --actor <cli>:<model>
```

## Shortcuts that fail (and are detected)
- Summarising or skipping a boring passage → content ratio < 95 % or 4-gram retention < 90 %.
- Padding with your own sentences to reach 95 % → retention stays fine but the observer compares
  added text against the base; it is reported as gate gaming.
- Writing 「講者提到…」 → new-summary-phrase gate.
- Doing punctuation colons or hooks now "to save a step" → those are p3-punct / p3-hooks; their gates prove
  what changed in each stage, and the observer flags bundled work.
