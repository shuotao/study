# Effort eval — which model × effort is enough for Phase 3

Question: the costliest judgment work is Phase 3 (polish → punct → hooks). Which model and reasoning effort
passes its gates reliably, and where does more effort stop paying?

Method (`pipeline/eval_effort.py`, reproducible):
- Fixture: `examples/talk-context/excerpt.srt` (60 cues, 936 Han characters, raw ASR style without punctuation).
- Each config runs the real headless loop: a fresh `claude -p` process per stage, gates re-run by the
  orchestrator, exact failures fed back, 3-round circuit breaker. Configs run sequentially, one run each.
- Recorded from the ledger, not from the agent's words: rounds per stage, gate failures, wall time, audit.
- Metrics on the final `cleaned.md`: content ratio vs Phase A text, 4-gram retention, paragraph median,
  hook growth (p3-hooks vs p3-punct), number of 「：」.

Limits: n = 1 per config on a short excerpt; this ranks configs, it does not prove small differences.
Quality beyond the gates was read blind by a separate judge (see below).

<!-- table -->
| config | p3 done | rounds polish/punct/hooks | gate fails | minutes | audit | ratio | 4-gram | para median | hook growth | colons |
|---|---|---|---|---|---|---|---|---|---|---|
| claude:haiku:medium | yes | 1/1/1 | 0 | 1.9 | green | 1.061 | 0.985 | 83.0 | 1.035 | 4 |
| claude:sonnet:low | yes | 1/1/1 | 0 | 1.1 | green | 1.059 | 0.988 | 78 | 1.038 | 4 |
| claude:sonnet:medium | yes | 1/1/1 | 0 | 1.2 | green | 1.077 | 0.982 | 72.0 | 1.038 | 1 |
| claude:opus:low | yes | 1/1/1 | 0 | 0.8 | green | 1.057 | 0.992 | 68 | 1.03 | 5 |
| claude:opus:medium | yes | 1/1/1 | 0 | 1.4 | green | 1.088 | 0.978 | 64.5 | 1.037 | 6 |
| claude:fable:low | yes | 1/1/1 | 0 | 2.1 | green | 1.107 | 0.975 | 73.5 | 1.072 | 4 |
<!-- /table -->

## Blind quality read (Opus 5.5, fresh context, outputs shuffled as A–F)

The judge diffed every output against the source character by character: **all six have 0 omissions and
0 changed words; every hedge (「再看看」「原則上應該可以」「應該」) survived.** Zero omission held for every model —
the gates and the architecture do that work. The differences are only in what was *inserted*.

| rank | blind | config | distortions (inserted claims) | punct | para | headings | hooks | overall |
|---|---|---|---|---|---|---|---|---|
| 1 | B | **opus · low** | 0 | 5 | 4 | 4 | 5 | **5** |
| 2 | A | sonnet · low | 0 | 5 | 4 | 3 | 3 | 4 |
| 3 | D | opus · medium | 0 | 4 | 3 | 5 | 3 | 4 |
| 4 | E | sonnet · medium | 1 | 3 | 4 | 4 | 3 | 3 |
| 5 | F | fable · low | 2 | 5 | 4 | 4 | 1 | 3 |
| 6 | C | haiku · medium | 2 | 2 | 2 | 4 | 2 | 2 |

Key: `docs/qaqc/eval-blind-key.json`. Judge's verdict: B and A publishable as is; D, E small fixes; F remove
two claim-adding hooks; C needs rework (missing 「」, a sentence boundary error, a list broken by a paragraph).

## Conclusions (hypotheses at n = 1, stated as such)

1. **More effort did not buy quality here.** Low beat medium for both Opus and Sonnet; the short excerpt
   leaves little room for reasoning to pay off. Default Phase 3 implementer → **Opus 5.5 · low**
   (best and fastest, 0.8 min); budget alternative → **Sonnet 5.5 · low**. Not Haiku for Phase 3.
2. **Fable is not needed as an implementer.** It wrote the most hooks (growth 1.072) and two of them invented
   links. Keep Fable in the orchestrator seat, where judgment about *process* matters more than prose.
3. **The gap the gates cannot see is hook content.** "Insert-only" is proven mechanically, but a hook that adds a
   claim (「會這樣拿出來討論的原因是：」) passes. This is now an explicit observer check (S10 in
   `prompts/observer.md`) and a rule line in `prompts/rules.md` § R8.
4. Re-run on the full talk before tightening further; small-N rankings can flip.
