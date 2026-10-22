# Stage p2-translate — Phase 2: timeline-locked zh-TW track (study srt_zhtw.py, unchanged)

Role: implementer. Rules: `prompts/rules.md` § R5, § R9. Target: Traditional Chinese (Taiwan), zh-TW.
Proven in study on English talks (AU2026, Revit MEP, Koshi); a cleaned non-English source runs with `--keep-all`.

You never see or write a timecode. `scripts/lang/en/srt_zhtw.py prep` already produced:
- `sessions/<slug>/p2/source.txt` — `<id>\t<source text>` per line (English hallucination cues already dropped)
- `sessions/<slug>/p2/segments.json` — do not edit
- `sessions/<slug>/p2/zh_parts/` — empty; you fill it

## Do
1. Translate in batches of ~40 lines. Read 3 lines before/after as context (subtitles break mid-sentence), but
   translate each id on its own: 1:1, never move words from one id into another.
2. Write each batch as `p2/zh_parts/part_<first>-<last>.json` = `{"<id>": "<譯文>", …}`.
3. Faithful and complete; no explanatory brackets; official product terms kept; `sessions/<slug>/glossary.json`
   (if present, `{"English term": "譯名"}`) is mandatory; Taiwan glyphs (裡、群、台) — no Simplified characters.
4. A cue that is a fluent hallucination (unrelated to the talk) → add its id to `p2/drops.json` (JSON list) and
   do not translate it.
Unattended alternative for long talks: `python3 scripts/lang/en/srt_translate_zhtw.py sessions/<slug>/p2`
(batches through headless Antigravity; same output contract).

## Finish
```bash
python3 scripts/lang/en/zh_parts_check.py sessions/<slug>/p2 [--glossary sessions/<slug>/glossary.json]
python3 gsn.py done <slug> p2-translate --actor <cli>:<model>    # assembles transcript.zh-TW.srt, proves every timecode
```
