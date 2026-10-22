# Worker prompt: quadrant I diagrams, diagrams.json v1 (Sonnet)

Purpose: draw small diagrams for the points on the I page that have "a process or relationships", to help beginner readers see the structure. You write only `diagrams.json` (the judgment); the diagrams are produced deterministically by `tools/render_diagram.py`.

Write all user-facing text (node text, arrow labels, `title`, `note`) in Traditional Chinese (zh-TW), full-width punctuation.

Read first:
- `docs/SPEC.md` §13.1 (including W4a, W5, W9), §13.2, §13.6
- `prompts/_provenance.md`
- `runs/<run>/K.json`, `source.anchors.json`, `meta.json` (the reader)
- `runs/<run>/i.html`: the diagram must fit the card text; it must not contradict the card, and must not duplicate the whole card

Choosing diagrams:
- Draw only for K points whose source really has "order, causality, composition, route, or contrast"; if none, draw none. 3-5 diagrams per session is enough.
- Types:
  - `flow`: steps with an order
  - `loop`: the speaker themself says it returns to the start or keeps cycling
  - `hub`: one core connected to several components
  - `chain`: places or a route strung together

Nodes and arrows (this is the high-risk zone for hallucination):
- Every node and every arrow needs `anchors`, and may use only that K's anchors. Before writing, quote the source fragment in your draft.
- **An arrow represents a relation and is the easiest place to fabricate causality.** Draw an arrow only when the source explicitly states a relation such as 「然後／接著／所以／為了／串到」 (then / next / so / in order to / connects to). If the source merely lists things in parallel, use `hub` or leave arrows without labels.
- The back edge of a `loop` may be drawn only when the speaker said 「再回饋／再調整／持續更新」 (feed back again / adjust again / keep updating), and must use `dashed: true`.
- When the source is a hypothesis or hope (假設、希望、打算、如果), the edge or note must keep the qualifier, e.g. `note: "講者假設明治橋恢復"` (the speaker assumes Meiji Bridge is restored), with `note_anchors`.
- Node text <= 18 Chinese characters, using the speaker's words. Terms follow SPEC §13.1 W4a: prefer words the card has already explained, otherwise use the source's plain wording.
- Arrow labels <= 6 Chinese characters, may be omitted.
- Limits: <= 9 nodes, <= 12 arrows. For beginners, 5-7 nodes is best.
- `title` uses third-person attribution (「…（沈伯洋的說法）」 "... (Shen Boyang's account)"), not written as fact.

Format: see the header of `tools/render_diagram.py`. Use `id` of the form `d-k<n>`, at most one diagram per K.

Self-check:
```
python3 tools/render_diagram.py runs/<run> && python3 tools/diagram_check.py runs/<run> && python3 tools/k_check.py runs/<run>
```
All three must PASS. Also open `verify/i_diagrams.png` and look: nodes must not overlap, text must not be cropped, arrow directions must be correct.

Write only `diagrams.json`; `i.html` is embedded by the tool, do not edit it by hand. Reply with: each diagram's K, type, node count, and arrow count, and the source relation word each arrow relies on.

## v1.1 addendum (2026-10-12, Shen Boyang session persona: solid-line boxes made proposals look decided)
- Every node must have `status`:
  - `existing`: the present situation the speaker describes or something that already happened
  - `proposed`: the speaker's proposal, plan, or hope
  - `hypothetical`: the speaker's hypothetical scenario, e.g. 「假設明治橋回來」 (suppose Meiji Bridge comes back)
  The tool draws these as solid / dashed / dotted boxes and automatically adds a legend under the diagram.
- Only words that appear in the source may go into nodes. Do not write 「中央可以做什麼」 (what the central government can do) as 「中央補助」 (central subsidy).
- Only when the speaker says 「之後／接著」 (afterwards / next) is it an order. Things the speaker lists together in the same passage (e.g. what the service team explains in one go) should be drawn as one node, or as a hub around a core, not strung into a sequential flow.
- If the speaker says something comes "after" other things, do not put it on the same hub as those things.
- Arrow labels must be understandable to a beginner (e.g. write 「假設明治橋恢復」, not 「若橋恢復」). Limit 6 characters; when it does not fit, rewrite it as a `note`.

## When a gate seems wrong (escalate; never bend the content) — Observer 2026-10-13
- A gate failure is a signal, not an order to change the text. Before editing, decide which it is: (a) the product really violates the rule -> fix the product by the rule's own remedy (e.g. add the gloss the jargon gate asks for); (b) the gate is wrong or too blunt for this session (false positive, wrong scope, rule contradicts another rule).
- If (b), **do not make the gate pass by changing what the speaker said**: do not delete or replace the speaker's word, drop a unit, loosen an anchor, split one claim to dodge a length cap, or reword into something the source does not say. A product that passes by being less faithful is worse than a red gate.
- Instead: leave the content faithful, stop, and report in your reply under a heading `GATE DISPUTE`: gate id + exact failure line, the source paragraph id and quote it conflicts with, why you think the gate is wrong, and the smallest change (to a tool or a per-run file such as `jargon.txt`) that would fix it. The orchestrator fixes the tool or decides; you do not.
- If you did make any workaround to get green, say so explicitly under `WORKAROUNDS` (what you changed and why). Silence about a workaround is a defect.
- Never "fix" a count, id, or status field by hand to match the checker; counts are derived by tools.

## Legibility floor (Observer 2026-10-13)
- Diagram text must stay >= 14px at the size the reader sees it (SPEC font floor; `ui_check` U1 scales SVG by its rendered width). The tool draws at natural size; do not ask for more nodes per row, longer labels, or more nodes overall to fit a message: if a diagram needs shrinking to fit, it has too much in it. Split into two diagrams or use a `note`.
- Node text <= 3 lines; arrow labels <= 6 characters (existing rule). A U1 red on a diagram is a content-size problem to report, never a reason to shrink the font in the data.
