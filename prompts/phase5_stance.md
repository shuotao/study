# Stage p5-stance — Phase 5: stance notes (好學生筆記) → notes_<identity>.md

Role: implementer. Rules: `prompts/rules.md` § R0.4, § R3. The identity is on the task card
(`metadata.json.identity`), e.g. 建築師, 小學老師, 軟體工程師.

## Do
1. Start from the input named on the task card (enhanced.md when Phase 4 ran, else cleaned.md); copy it to
   `notes_<identity>.md` and keep every original line.
2. Add the 📝 learning-summary block right after the `#` title (before the first `##`).
3. After paragraphs that carry a core concept, add a 🎯 block in the identity's language (類比／應用／連結).
   Typically one per `##` section; quality over count. The analogy must hold logically.
4. End with the 💡 core-insight block.
5. Only add `>` blocks. Never edit, move or delete original text.

## Finish
`python3 gsn.py done <slug> p5-stance --actor <cli>:<model>`
