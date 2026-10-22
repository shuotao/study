# Worker prompt: claims extraction v1 (quadrant III, Sonnet)

Read:
- `runs/<run>/source.anchors.json`
- `docs/SPEC.md` §13.1, §13.5

Task: extract "claims / conditions / exceptions / steps / numbers" from the source, for expert lookup.
- Each claim should use the source's own wording as much as possible; you may only delete spoken filler words; do not rewrite the meaning, and do not merge different claims from different paragraphs.
- type is one of {主張 (claim), 條件 (condition), 例外 (exception), 步驟 (step), 數字 (number)} (主張 = an unconditional general statement; use 條件 only when there is 如果/只要/除非/限制, i.e. if/as long as/unless/limit). The type values are written in Chinese exactly as listed; tools match them.
- anchors: ids of the paragraphs where the claim appears, at least 1, and they must really contain the claim.
- Coverage: at least 3 entries per `##` section of the source (gate minimum: 2). Total: at least max(20, 0.3 × paragraphs), at most 90; numbers: at least max(4, 0.06 × paragraphs) (gate T4 in `tools/iii_check.py`).
- Write the `claim` field in the source's language (Traditional Chinese, zh-TW), full-width punctuation.

Output: write only `runs/<run>/claims.json`, in the format
`[{"cid": "c01", "claim": "...", "type": "...", "anchors": ["p0012"]}]` (cid in sequence c01, c02, ...; it is a stable id and must not be renumbered in repair rounds; when deleting a row, keep the other cids unchanged)

Do not write other files. Reply with only the total and the count per type.

## Type tie-break rules (lessons from claims r1-r3, 2026-10-12)
- `條件` (condition): only when a trigger word (如果／只要／除非／當…時／一旦／假設) **explicitly appears** in the source substring and the claim depends on that trigger. A general statement without a trigger word -> `主張` (claim).
- For prompt text or demo actions inside a demo, the substring must include the framing words (「如果我輸入：」"if I type:", 「我告訴它」"I told it"), otherwise do not include it.
- Keep attribution and hedges (「我聽到」"I heard", 「理想上」"ideally", 「應該」"should").

## When a gate seems wrong (escalate; never bend the content) — Observer 2026-10-13
- A gate failure is a signal, not an order to change the text. Before editing, decide which it is: (a) the product really violates the rule -> fix the product by the rule's own remedy (e.g. add the gloss the jargon gate asks for); (b) the gate is wrong or too blunt for this session (false positive, wrong scope, rule contradicts another rule).
- If (b), **do not make the gate pass by changing what the speaker said**: do not delete or replace the speaker's word, drop a unit, loosen an anchor, split one claim to dodge a length cap, or reword into something the source does not say. A product that passes by being less faithful is worse than a red gate.
- Instead: leave the content faithful, stop, and report in your reply under a heading `GATE DISPUTE`: gate id + exact failure line, the source paragraph id and quote it conflicts with, why you think the gate is wrong, and the smallest change (to a tool or a per-run file such as `jargon.txt`) that would fix it. The orchestrator fixes the tool or decides; you do not.
- If you did make any workaround to get green, say so explicitly under `WORKAROUNDS` (what you changed and why). Silence about a workaround is a defect.
- Never "fix" a count, id, or status field by hand to match the checker; counts are derived by tools.
