# Stage p6-matrix — Phase 6: Good-Student Matrix (好學生矩陣)

Role: the ORCHESTRATOR runs this stage and dispatches one worker per data file. Spec: `matrix/SPEC.md`.
`gsn.py` already ran `python3 matrix/tools/n.py init sessions/<slug> <slug>` (anchors, II page, hub).

Quadrants: II full text (done by the tool) · I key-point cards · III deep reading · IV cross-session links.

## Steps — one at a time, each gated before the next (SPEC §8)
| # | Data file | Prompt (worker) | Gate |
|---|---|---|---|
| 1 | `speakers.json` (only if the talk has audience Q&A) | SPEC §13.1 W10 | used by later gates |
| 2 | `K.json` 5–7 key points | `matrix/prompts/worker_k.md` (Sonnet) | `matrix/tools/k_draft_check.py` |
| 3 | confirm K: set `status` to contain 「已確認」 | the user; unattended: the orchestrator, adding `"confirmed_by"` | — |
| 4 | `claims.json` (III) | `matrix/prompts/worker_claims.md` + `_provenance.md` | `iii_check.py`, `provenance_check.py --view claims` |
| 5 | `i.json` (I cards) | `matrix/prompts/worker_i.md` + `_provenance.md` | `k_check.py` after build |
| 6 | `diagrams.json` (optional) | `matrix/prompts/worker_diagram.md` | `diagram_check.py` |
| 7 | `iv.json` (III deep-dive topics) | `matrix/prompts/worker_iv_json.md` | `iv_check.py` |
| 8 | links: `python3 matrix/tools/n.py links`, judge every candidate → `matrix/links/links.json` (a single session: `{"judged_by": "orchestrator", "links": [], "excluded": []}`) | `matrix/prompts/worker_links.md` (Haiku triage → Sonnet type+why) | `links_check.py` |
| 9 | build | `python3 matrix/tools/n.py build <slug>` | — |
| 10 | verify (fresh context) | `matrix/prompts/verifier.md` (Opus); on failure `matrix/prompts/observer.md` | SPEC §10 |

Repair loop: max 3 rounds per artifact, then circuit-break and report. The orchestrator re-runs every gate
itself; never trust a worker's "I checked".

## Finish
```bash
python3 matrix/tools/n.py check <slug>
python3 gsn.py done <slug> p6-matrix --actor <cli>:<model>
```
Open `matrix/runs/<slug>/index.html` in a browser (works from file://).
