# Worker prompt: quadrant IV content data iv.json v1 (Sonnet), three short-text cards

> **Role update (2026-10-13).** IV is now the cross-session breadth page (it links key-point cards across sessions; see `prompts/worker_links.md` and `docs/SPEC.md` §2 and §13.8). The `iv.json` produced by this prompt is **no longer rendered as a page of its own**; it is used only as the source of the III deep-dive topics (`tools/topics.py` reads it to produce `topics.json`). The schema below is unchanged.

The IV reader is someone familiar with the field who wants to know three things within 5-8 minutes:
- What is new in this talk
- How hard the evidence is
- What to follow up on

You write only the content data `runs/<run>/iv.json`. `tools/topics.py` turns its questions and gaps into III deep-dive topics (`topics.json`); `tools/iv_check.py` validates it. **Do not write HTML.**

Write all user-facing text (headline, claim, evidence, questions, quotes, lead) in Traditional Chinese (zh-TW), full-width punctuation.

Read first:
- `docs/SPEC.md`: §13.1 (including W4a, W5, W9, W10), §13.3, §13.4
- `prompts/_provenance.md`
- These files of the run: `meta.json`, `K.json`, `source.anchors.json`, `speakers.json` (if any), `aux.anchors.json` (if any), `claims.json` (deep-study runs always have it; this prompt is only used for deep-study runs)

For the format see the schema below and the header of `tools/iv_check.py`. One entry per K, in the order K1-Kn.

## How to write (for humans to read, not an audit table)
- **headline**: one line, in an expert's voice, stating the substance of the point, not merely the topic name.
- **claim**: 1-3 complete sentences saying what the speaker claims, with conditions and qualifiers written into the sentence (if, ideally, the speaker relays...). <= 120 characters.
  - The speaker's words are attributed in the third person.
  - A full-sentence quotation uses 「」 and must be a contiguous substring of the source.
- **evidence**: at most 5 items, each one a complete sentence.
  - Only put things that really happened in the demo (kind=event), concrete methods the speaker gave (kind=method), and numbers (kind=number).
  - What the audience said gets src=audience; handouts get src=aux with refs as hNNN.
  - General statements go in claim, not here.
- **questions**: at most 5 items. This is the field experts care about most.
  - Write them as questions that can be asked directly, or as things to verify.
  - kind is one of unsupported (no basis given) / hedged (the speaker hedged) / relayed (relayed from others) / unclear (recording unclear) / absent (a gap the speaker named themself) / ext (needs external verification; write only what to verify, not the answer).
  - Judge only from the source itself; add no external knowledge and do not evaluate.
- **gaps**: every item of `meta.expert_checklist` must be listed, with value 「有」 (present) or 「原文未提」 (not mentioned in the source). 「有」 is allowed only if the speaker really provided it in that K's anchor paragraphs.
- **quotes**: 1-3 source quotations that best represent the point, ref set to the anchor. They are collected under "expand source quotations".

## Iron rules
- Every item must have refs, using only that K's anchors (hNNN for handouts).
- Prefer omission over padding: if there is nothing to write, write less; do not pad.
- Evidence plus questions total <= 12 items.

## Self-check
```
python3 tools/iv_check.py runs/<run>
python3 tools/n.py build <run>
python3 tools/k_check.py runs/<run>
```
All must PASS, and take a look at `verify/iv.png`.

Write only `iv.json`. Reply with: the number of evidence and questions items per K, and the gate results.


## v1.1 (2026-10-12)
- `lead` says only who the speaker is and what they claim (1-2 sentences); **it must not name any K and must not say which points had more demo**. Whether a point is 值得細讀 (worth close reading) or 可略 (skippable) is determined mechanically by the tool; restating it in the lead would conflict with the grading (iv_check J6).
- Layout is produced by the shared components of `tools/ui.py` (SPEC §6); do not write any HTML or styles.

## When a gate seems wrong (escalate; never bend the content) — Observer 2026-10-13
- A gate failure is a signal, not an order to change the text. Before editing, decide which it is: (a) the product really violates the rule -> fix the product by the rule's own remedy (e.g. add the gloss the jargon gate asks for); (b) the gate is wrong or too blunt for this session (false positive, wrong scope, rule contradicts another rule).
- If (b), **do not make the gate pass by changing what the speaker said**: do not delete or replace the speaker's word, drop a unit, loosen an anchor, split one claim to dodge a length cap, or reword into something the source does not say. A product that passes by being less faithful is worse than a red gate.
- Instead: leave the content faithful, stop, and report in your reply under a heading `GATE DISPUTE`: gate id + exact failure line, the source paragraph id and quote it conflicts with, why you think the gate is wrong, and the smallest change (to a tool or a per-run file such as `jargon.txt`) that would fix it. The orchestrator fixes the tool or decides; you do not.
- If you did make any workaround to get green, say so explicitly under `WORKAROUNDS` (what you changed and why). Silence about a workaround is a defect.
- Never "fix" a count, id, or status field by hand to match the checker; counts are derived by tools.
