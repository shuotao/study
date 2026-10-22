# Stage p3-punct — Phase C: punctuation

Role: implementer. Rules: `prompts/rules.md` § R7.

## Do
1. Mechanical part — run the tool, do not do it by hand:
   `python3 scripts/normalize_punctuation.py sessions/<slug>/cleaned.md --in-place`
2. Judgment part (§ R7.2): read the text; where an announcer names what follows (…是／就是、…說、noun header,
   speaker label, 例如、換句話說), change the comma/period after it to 「：」 and add 「」/『』 around quoted speech.
3. Change **punctuation only**. Not one content character may change; paragraph count stays the same.

## Finish
```bash
python3 scripts/normalize_punctuation.py sessions/<slug>/cleaned.md --check   # must print 0
python3 gsn.py done <slug> p3-punct --actor <cli>:<model>
```
The gate proves "only punctuation changed" by comparing content characters with the snapshot taken when
this stage opened. Any wording fix you think is needed: write it to `corrections.json`, do not apply it here.
