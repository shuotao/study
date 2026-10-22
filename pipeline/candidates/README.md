# candidates/ — rewritten tools that are not the default (kept only to re-run the comparison)

`gsn.py` never calls these. Verdicts and numbers: `docs/qaqc/tool-comparison.md`.

| File | Replaced | Verdict |
|---|---|---|
| `transcribe_groq.py` | `groq_transcribe.py`, `groq_transcribe_en.py` | rejected: −18 % content and a fabricated cue on a Chinese clip |
| `translate_srt.py` | `srt_zhtw.py` + `zh_parts_check.py` | rejected: identical output, 12 false Simplified alarms (核准) |
| `phase_a_clean.py` | `SRT/qaqc_srt.py` | superseded: won round 1; after the fix went upstream the original ties or beats it (round 2). `--phase-a candidate` |
| `compare.py` | — | the harness: `python3 pipeline/candidates/compare.py phase-a|transcribe|translate` |

Every idea worth keeping from these files has been ported upstream to study (Phase A exemptions, resumable transcription).
