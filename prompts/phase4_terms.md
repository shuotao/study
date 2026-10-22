# Stage p4-terms — Phase 4: term supplements → enhanced.md

Role: implementer. Rules: `prompts/rules.md` § R0.4, § R4.

## Do
1. Copy `sessions/<slug>/cleaned.md` to `sessions/<slug>/enhanced.md`.
2. Pick the terms a newcomer would not know (product names, methods, jargon, acronyms). If the user gave a
   keyword list in `context.txt`, include those.
3. After the paragraph where each term FIRST appears, add one block (format § R4). 2–4 sentences, plain words,
   general knowledge only; never attribute anything to the speaker; one block per term.
4. Do not change a character of the original paragraphs or headings.

## Finish
`python3 gsn.py done <slug> p4-terms --actor <cli>:<model>` — the gate removes every `>` block and requires
the remainder to equal cleaned.md exactly.
