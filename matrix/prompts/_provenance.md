# Shared fragment: per-unit provenance pass v1

Applies to any view that "turns source text into another form": reading guide, diagram, claims table, decision card, video script, translation, summary.
Independent of session, language, and domain. The rules in this fragment outrank any "write it shorter", "compress", or "match the spec phrase" instruction in a worker prompt:
**write less and split finer rather than write a unit that cannot be traced to source.**

(Language note: this prompt is in English because it is for AI. Any user-facing text the worker produces stays in Traditional Chinese (zh-TW) with full-width punctuation. Chinese qualifier words listed below are kept verbatim because the source text is Chinese and tools match them.)

## 〇、Terms

- **Unit**: the smallest independently checkable block of content in the product. Depends on the view: a sentence, a diagram cell, a claim, a decision option, a scene narration.
  If a unit contains several things (joined by 與 "and", 且 "and", 、 "and/comma"), count each thing separately and trace each one separately.
- **Anchor**: a paragraph id of the source, e.g. `p0066`, present in `source.anchors.json`.
- **Evidence quote (quote)**: a contiguous substring of the anchor's source paragraph.
- **Qualifier**: a word that changes the strength, scope, or attribution of a claim. At minimum:
  - Condition: 如果／假如／只要／當／除非／一旦／if／when／unless／as long as
  - Modality: 可能／也許／應該／可以／必須／理想上／通常／大約／maybe／should／can／might／ideally
  - Source and attribution: 我聽到／他說／在另一場簡報／有人認為／according to／I heard
  - Scope and examples: 例如／像是／部分／一些／有時／for example／some／sometimes
  - Negation and contrast: 不／沒有／但／不過／而不是／not／but／instead of
  - Causal words: 因為／所以／因此／because／so／therefore (see §三 rule 5)

## 一、Order of actions (must not be reversed)

1. **Take the evidence first, then conclude.** For each unit, first find the sentence in the source it depends on, copy that sentence as the `quote`; only then write the unit's text.
   Do not write the text first and then go looking for "a roughly nearby paragraph" to attach.
2. **One unit, one row.** Before writing the product, write out the table below (in a working draft or in your reasoning), one row per unit:

   | unit text | each thing it depends on | anchor of that thing | quote (contiguous substring of source) | qualifiers (present in source) | does the unit keep them |
   |---|---|---|---|---|---|

3. The product's text and anchors are derived from this table. **The product must not contain anything that is not in the table.**

## 二、Five questions every unit must pass

Answer each for every unit. Any "no" means the unit must be changed.

1. **Is there a quote?** Does every thing in the unit have a quote?
2. **Is the quote inside this anchor?** Paste the quote into the source text of the pNNNN you labeled: is it a contiguous substring?
   If not, the anchor is wrong. Find the paragraph that really contains the sentence and **change the anchor, not the quote**. If the content spans several paragraphs, list all of them as the unit's anchors, or split the unit.
3. **Neighbor-paragraph trap check.** Speakers often finish one concept over two or three paragraphs; the noun, the conclusion, or the action verb often lands in an adjacent paragraph.
   For each unit, search each of its key words in the paragraph(s) you labeled; for any you cannot find, search 3 paragraphs before and after; if found there, your anchor is wrong or incomplete.
4. **Are the qualifiers kept?** Look at one sentence before and after the quote in the source: is there any qualifier from the §〇 list? If so, the unit must keep it in the shortest possible form;
   if it does not fit, shorten the subject or split into two units. **Never drop the qualifier and keep the claim.**
   Especially:
   - Something "relayed, ideal, or hypothetical" must not be written as the speaker's own firm fact.
   - "Only when the condition holds..." must not be written as an unconditional rule.
   - 應該／可能／也許 (should/may/perhaps) must not be written as certain.
5. **No added causality, order, or scope?** Any 所以／因此／because／導致／使得／然後 you add: does the source have the same relation? Two adjacent sentences each being true does not mean one causes the other.
   If the speaker says "A, and also B, because C", do not write "A so B".
   Do not change 例如 (for example) to 所以 (so); do not change 部分 (some) to 全部 (all); do not change "one of them" to "all".

## 三、Special rules

1. **Headings are not the speaker's words.** Section headings, subheadings (`sections`, `subsection`), file names, and captions are added by the editor. A content claim must not come only from a heading.
2. **Slide text is not a claim source** (SPEC §13.1 W4). **Passages marked 〔錄音不清〕 (recording unclear) are treated as nonexistent**: do not guess or fill them in, and do not write the sentence right next to them as certain.
3. **Use the speaker's words.** Do not substitute synonyms, especially for proper nouns, tool names, and terms. Where the speaker says 工具 (tool) do not write "agent"; where the speaker says 提示 (prompt) do not write 請求 (request).
4. **Parallel languages must be equivalent.** When producing two language versions of the same content, the set of claims must be identical: a point, qualifier, or framing word kept in one version must also be in the other.
5. **Causal-word whitelist.** A unit may use a causal word only when the quote itself contains an explicit causal word (因為／所以／因此／由於／because／so／therefore／that's why),
   and the direction and subject/object of the causality must match the quote. Otherwise use a neutral connective (並、而、另外 / and, also).
6. **Splitting composite units.** If a cell or sentence contains something you want to include but cannot find in your labeled anchor, use these three options in order:
   a. Add another paragraph that contains it to the unit's anchors (if the view's format allows multiple anchors);
   b. Split the unit in two, each with its own anchor;
   c. Delete that thing.
   **Never** keep it while attaching an anchor that does not contain it.
7. **Multi-column correspondence.** In a table or comparison, the columns of one row are independent units. "Example A -> result B" may be placed side by side as cause and effect only if the speaker explicitly says B is the result of A;
   otherwise place them side by side without a connecting line, and trace each column separately.
8. **When the spec conflicts with the source, the source wins.** If a phrase listed in the spec cannot be found in the source (or conflicts with it), do not copy it. Write what the source says, and list it under `deviations` in your report.
9. **Numbers.** A numeric unit needs three things: the number, the thing it describes, and its qualifier (約 about, 多於 more than, 最多 at most, 理想 ideal). All three must be in the quote. A number with unclear units is handled per SPEC §13.1 W4.

## 四、Minimum output record

Each view's working draft (`verify/<view>_provenance.json`) contains at least one entry per unit:
```json
{"id": "<panel/cell, sentence number, or claim number>", "text": "...",
 "units": [{"claim": "...", "anchor": "pNNNN", "quote": "..."}],
 "qualifiers": ["..."]}
```
This draft serves both `matrix/tools/provenance_check.py` and the Verifier. The draft may stay under verify/; it does not count as an extra product.

## 五、Self-check before finishing

1. Use a script to confirm every `quote` is a contiguous substring of the source paragraph of its `anchor` (one line of Python is enough). If any fails, you cannot report.
2. If `matrix/tools/provenance_check.py` exists, run it and handle every `FAIL` (key word missing from the anchor and that word appears in a neighboring paragraph) and `WARN` (a qualifier may have been dropped).
3. For every `WARN` and `FAIL`: do not just quietly fix it; go back and re-answer the five questions in §二.
4. In your report, state the number of units you deleted, split, or changed because they could not be traced (write 0 if none).
