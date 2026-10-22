# Worker prompt: key-point set K.json first draft v1 (Sonnet)

Read first: `matrix/SPEC.md` §13.1 (especially W5, W6, W9) and §2.
Input: `matrix/runs/<run>/source.anchors.json` (each paragraph is `{id, section, text}`; the source is the only basis).

Produce `matrix/runs/<run>/K.json`. Write all user-facing text (`point`, `i_angle`) in Traditional Chinese (zh-TW), full-width punctuation:
```json
{"status": "初稿，待確認（2026-10-13，worker_k v1）",
 "K": [{"k": "K1", "point": "一句話重點", "anchors": ["p0012", "…"],
        "i_angle": "給初學者的切入提示（附段落編號）"}]}
```
(English gloss of the placeholders: status = "draft, awaiting the user's confirmation (2026-10-13, worker_k v1)"; point = "one-sentence key point"; i_angle = "entry hint for beginners (with paragraph ids)". The status string is required wording; keep it verbatim in Chinese.)
(From 2026-10-13, do not write iv_angle: IV is now breadth; deep-dive hints go into III's topics.json with kind=deep.)

Rules:
1. 5-7 key points, in the order the speaker presented them; together they should represent the backbone of the talk, not the flashiest picks.
2. `point` <= 40 Chinese characters (hard cap 45), using the speaker's words (SPEC §13.1 W5); do not add causality, universal claims, or turns that are not in the source.
3. `anchors`: the paragraphs that support the point, 3-20 per point recommended (cap 35); they must exist; avoid overlap between points.
4. Audience questions, host transitions, and pure pleasantries must not be taken as the speaker's key points.
5. Cross-session matching uses `point` and the anchors' source text to find relations, so `point` must contain a **concrete topic word** (product, method, concept name), not a vacuous sentence like 「重要的是意圖」("what matters is intent").
6. Write only K.json; do not change other files. When done run `python3 matrix/tools/k_draft_check.py matrix/runs/<run>`; it is complete only when all green.

Reply with only: for each session the K1-Kn points (one per line) + the k_draft_check result.

## When a gate seems wrong (escalate; never bend the content) — Observer 2026-10-13
- A gate failure is a signal, not an order to change the text. Before editing, decide which it is: (a) the product really violates the rule -> fix the product by the rule's own remedy (e.g. add the gloss the jargon gate asks for); (b) the gate is wrong or too blunt for this session (false positive, wrong scope, rule contradicts another rule).
- If (b), **do not make the gate pass by changing what the speaker said**: do not delete or replace the speaker's word, drop a unit, loosen an anchor, split one claim to dodge a length cap, or reword into something the source does not say. A product that passes by being less faithful is worse than a red gate.
- Instead: leave the content faithful, stop, and report in your reply under a heading `GATE DISPUTE`: gate id + exact failure line, the source paragraph id and quote it conflicts with, why you think the gate is wrong, and the smallest change (to a tool or a per-run file such as `jargon.txt`) that would fix it. The orchestrator fixes the tool or decides; you do not.
- If you did make any workaround to get green, say so explicitly under `WORKAROUNDS` (what you changed and why). Silence about a workaround is a defect.
- Never "fix" a count, id, or status field by hand to match the checker; counts are derived by tools.
