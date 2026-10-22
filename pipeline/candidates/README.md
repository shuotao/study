# candidates/ — rewritten tools that LOST their head-to-head (kept only to re-run the comparison)

`gsn.py` never calls these. Verdicts and numbers: `docs/qaqc/tool-comparison.md`.

| File | Replaced | Verdict |
|---|---|---|
| `transcribe_groq.py` | `groq_transcribe.py`, `groq_transcribe_en.py` | rejected: −18 % content and a fabricated cue on a Chinese clip |
| `translate_srt.py` | `srt_zhtw.py` + `zh_parts_check.py` | rejected: identical output, 12 false Simplified alarms (核准) |
| `compare.py` | — | the harness: `python3 pipeline/candidates/compare.py phase-a|transcribe|translate` |

The winning candidate was promoted to `pipeline/phase_a_clean.py`.
