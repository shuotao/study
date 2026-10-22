# Worker prompt: cross-session key-point-card relation judgment v1 (Sonnet)

Input: `matrix/links/batch_<n>.json`; each candidate pair has two cards (session, K, point, excerpts of anchor source text) and `shared` (the literal shared words; **only the reason they were paired, not evidence**).
Example (34 pairs already judged): `matrix/links/links.json`. Spec: `matrix/SPEC.md` §2 (IV), §4 and §13.8.

Every pair **must** be judged as exactly one of:
- Related: `{"a","b","type","why"}`, type is one of 呼應／延伸／實例／對照／不同看法 (written in Chinese exactly as listed; tools match them)
  - 呼應 (echo): both sides make the same point. 延伸 (extension): one side goes one step further on the basis of the other. 實例 (instance): one side is a concrete case of the other's point.
  - 對照 (contrast): the same problem, different approaches. 不同看法 (differing view): the statements are in tension or contradict each other.
- Excluded: `{"a","b","why"}`, with the reason written out (e.g. 「字面都有『模型』：一邊是 CAD 模型，一邊是 AI 語言模型」 "both literally contain 'model': one is a CAD model, the other an AI language model"; 「只共用一般詞」 "only share a generic word").

Rules:
1. The basis for judgment is the two cards' point **and the anchor source text**, not the shared word. Read the anchor paragraphs in `matrix/runs/<run>/source.anchors.json` when needed.
2. Prefer omission over padding: it counts as related only if a reader would say "yes, these two sessions are talking about related things". Sharing a broad topic like "AI" or "BIM" is not enough.
3. `why` <= 60 Chinese characters, says clearly "where they are related", mentions both sides; must not add statements that are not in the source. Write `why` in Traditional Chinese (zh-TW), full-width punctuation.
4. **Every `why` (related and excluded) must be specific to this pair.** Name the concrete thing each side says (the product, method, or case), and for exclusions name what differs (e.g. which sense of a shared word each side uses). One generic sentence reused across pairs (「只共用一般詞」, 「主題不同」) is a defect: `links_check.py` L5 turns red when the same `why` appears more than 3 times, and a reviewer reads exclusions as public reasons. Before writing, scan your own `why` list; if two read alike, rewrite them with the pair's own nouns. Do not vary a generic sentence by one word to dodge L5; that is bending the content to pass the gate.
5. Output `matrix/links/judged_<n>.json`: `{"links":[...],"excluded":[...]}`; the number of pairs must equal the number of input pairs.

Spot-check budget: you are conservative by nature (measured recall 0.46-0.64). For every exclusion, ask once more "would a reader who read both sessions say these are connected?"; list the 3 least-sure pairs, preferring excluded ones.

Reply with only: how many pairs are related (with count per type), how many excluded, and the 3 pairs you are least sure about.

## When a gate seems wrong (escalate; never bend the content) — Observer 2026-10-13
- A gate failure is a signal, not an order to change the text. Before editing, decide which it is: (a) the product really violates the rule -> fix the product by the rule's own remedy (e.g. add the gloss the jargon gate asks for); (b) the gate is wrong or too blunt for this session (false positive, wrong scope, rule contradicts another rule).
- If (b), **do not make the gate pass by changing what the speaker said**: do not delete or replace the speaker's word, drop a unit, loosen an anchor, split one claim to dodge a length cap, or reword into something the source does not say. A product that passes by being less faithful is worse than a red gate.
- Instead: leave the content faithful, stop, and report in your reply under a heading `GATE DISPUTE`: gate id + exact failure line, the source paragraph id and quote it conflicts with, why you think the gate is wrong, and the smallest change (to a tool or a per-run file such as `jargon.txt`) that would fix it. The orchestrator fixes the tool or decides; you do not.
- If you did make any workaround to get green, say so explicitly under `WORKAROUNDS` (what you changed and why). Silence about a workaround is a defect.
- Never "fix" a count, id, or status field by hand to match the checker; counts are derived by tools.
