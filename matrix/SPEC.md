# Phase 6 — Good-Student Matrix: Consolidated Specification

Audience: AI agents running Phase 6 of this repo. Paths are repo-relative; code (`matrix/tools/`) is ground truth.
Tool registry: `docs/tools.md`. Role/model assignments: `docs/agents.md`. Ported from the author's private N project (2026-10).

---

## 1. Purpose & boundaries

N turns one lossless lecture transcript (a session's `cleaned.md` from Phase 3, which is the
好學生筆記 / quadrant II) into four ways of reading it — the four quadrants — and links
key points across sessions into a knowledge genealogy.

Hard boundaries (iron rules; never relax):

1. **The session is read-only.** Phase 6 only reads `sessions/<slug>/` (`cleaned.md`, images it references).
   Never write into a session directory, never touch its markers or ledger. Suspected ASR errors found here are
   *reported* to the user, not fixed in `cleaned.md`.
2. **Local only.** Matrix pages are local HTML (`file://`). Nothing is deployed by any tool here.
3. **The source is immutable; everything in `matrix/` is a disposable derivative.** The only source of truth is
   the session `cleaned.md` (= II). Every file under `matrix/runs/`, `matrix/links/`, `matrix/vault/` can be
   deleted and regenerated (all gitignored). `views_check.py` V1 proves via sha1 that `cleaned.md` has not changed
   since anchoring.
4. **No secrets.** No tool in Phase 6 calls a paid API. Never write keys into code, docs, or logs.
5. **Step-by-step.** Each judgment step is done, gated, and (where required) confirmed before the next. No bundling
   several judgment steps into one pass.
6. **Model assignment is eval-first.** Only measured assignments go in `docs/agents.md`; untested ones are labelled
   planned.

---

## 2. The four quadrants

Two orthogonal axes:

- **Horizontal = content**: 完整 (complete: every paragraph) vs 重點 (key points: the same
  K set of 5–7 points).
- **Vertical = reader**: 初學 (beginner) vs 精通 (expert).

| | 完整 complete | 重點 key points |
|---|---|---|
| **初學 beginner** | **II 理解過程** `ii.html` — linear read of the full verbatim text | **I 建立入口** `i.html` — scan cards, one per K, with diagrams |
| **精通 expert** | **III 追查與檢核** `iii.html` — DEPTH | **IV 交換與判斷** `iv.html` — BREADTH |

- **II** (complete × beginner): the speaker's words, every paragraph, in order. Deterministic.
- **I** (key × beginner): one card per K. Makes a first-timer care in ~3 minutes and sends
  them into II. Same K set as IV.
- **III = DEPTH, outward, one session only.** Unit = sentence/paragraph. The reader selects
  any sentence → annotates → takes it out to Claude/Google → pastes findings back, marking
  一致／補充／矛盾 vs the speaker. III has nothing to do with other sessions.
  **III exists only for deep-study sessions**, signalled by the presence of `claims.json`.
  Sessions added only as genealogy nodes get I + IV, never III (`n.py build` renders
  `iii.html` only when `claims.json` exists).
- **IV = BREADTH, inward.** Unit = key-point card (the same card as I, K-numbered). Shows
  how this session's cards link to cards of the other sessions in the **same genealogy**
  (`meta.json.genealogy`, e.g. `AU2026`, `台北大洋流`; `matrix/links/links.json`). Sessions of other
  genealogies are never compared or shown. The graph shows the I-card plain-language headline;
  similarity/judgment uses the card's underlying source paragraphs.
- `index.html` (hub): 2×2 grid of the four quadrants; missing quadrants render greyed
  「尚未產出」; collapsible list of the K points.

The retired IV "depth page" (claim/condition/evidence/contrast/boundary/check fields,
deep/skim tiering, triage nav, copy-summary) and the retired STE prose / engineering sheet /
decision page / video live in `matrix/tools/_legacy/` and `matrix/runs/*/_legacy/`. Do not revive them.

---

## 3. Data files per run (`matrix/runs/<YYYY-MM-DD>_<code>/`)

Anchor ID formats: source paragraphs `pNNNN` (4 digits, 1-based, document order);
speaker-supplied aux material `hNNN` (3 digits). Card id (global) = `<run>#K<n>`.

| File | Written by | Schema / meaning |
|---|---|---|
| `source.anchors.json` | `anchor_source.py` (tool) | `{source: abs path of cleaned.md, source_sha1, title, subtitle, sections:[str], paragraphs:[{id:"p0001", section, subsection, text, sha1}]}`. Paragraph = one non-empty, non-heading, non-image line, split exactly as `pipeline/md_parse.parse()` (one paragraph = one line). |
| `meta.json` | `n.py init` (tool) + hand edits | `{title, short_title?, label, speaker, published_ii (URL or ""), reader_i, reader_iv, genre: tech\|policy, storage_key, genealogy, domain_identifiers[], non_content_numbers[], expert_checklist[], aux?:{file,label,allowed_in:["iv"]}}`. `genealogy` (required, the user decides; default `default`) names the knowledge genealogy the session belongs to; IV and cross-session candidates stay inside it. `label` is the short session name used in IV/vault (e.g. `AU4258 Fusion MCP`, `AS2564`). |
| `K.json` | judgment (`worker_k.md`) | `{status, K:[{k:"K1", point, anchors:[pNNNN], i_angle?}], changelog?, speaker_notes?}`. 5–7 points, K1..Kn in speaker order; `point` ≤45 CJK (target ≤40) naming concrete topic words; 3–35 anchors each. `status` must contain the literal 「已確認」 only after the user (or, unattended, the orchestrator recording `confirmed_by`) confirms (anything else, e.g. 「初稿，待確認」, is unconfirmed). `iv_angle` is retired (do not write). |
| `i.json` | judgment (`worker_i.md`) | `{title, items:[{k, headline, anchors:[⊆ K anchors], paras:[{text, gloss?:{term, text, after?}}], more:[pNNNN]}]}`. Items in K order; 2–3 paras per card, ≤35 CJK per sentence. |
| `claims.json` | judgment (`worker_claims.md`) | `[{cid:"c01", claim, type: 主張\|條件\|例外\|步驟\|數字, anchors:[pNNNN], speaker?: "audience"}]`. `claim` is a contiguous substring of an anchored paragraph (bold markers stripped), ≥8 CJK. `cid` is stable across repair rounds. **Presence of this file marks the run as a deep-study session.** |
| `topics.json` | `topics.py` (tool) + kept `deep` items | `[{k, kind, text, quote?, refs:[pNNNN]}]`. III "深挖題目". `kind` ∈ unsupported, hedged, relayed, unclear, absent, ext, gaps, deep. `deep` items (former `iv_angle`) are hand/worker-written and preserved across regenerations. |
| `iv.json` | judgment (`worker_iv_json.md`) | Now only the **source for topics** (not rendered by IV). `{title, lead, items:[{k, headline, claim:{text, refs}, evidence:[{text, refs, src: speaker\|audience\|aux, kind: event\|method\|number}], questions:[{text, refs, kind}], gaps:{<checklist item>: 有\|原文未提}, quotes:[{q, ref}]}]}`. `topics.py` turns `questions` + missing `gaps` into `topics.json`. |
| `diagrams.json` | judgment (`worker_diagram.md`) | `[{id:"d-k<n>", k, type: flow\|loop\|hub\|chain, title, desc, nodes:[{id, label, sub?, anchors, status: existing\|proposed\|hypothetical, accent?}], edges:[{from, to, label?, anchors, dashed?}], note?, note_anchors?}]`. ≤1 diagram per K. |
| `speakers.json` | judgment (attribution) | `{default:"speaker", paragraphs:{pNNNN:{who: audience\|mixed\|uncertain, audience_spans?:[str], candidate_audience_spans?:[str], note}}}`. Lists only non-pure-speaker paragraphs. Must exist before K is drafted for any session with Q&A. |
| `aux.anchors.json` | `anchor_aux.py` (tool) | `{source, sha1, label, items:[{id:"h001", section, text}]}`. Speaker's own material only (official handout). IV-only. |
| `jargon.txt` | hand | Optional per-run jargon list (one term per line); overrides `matrix/tools/jargon_common.txt` for `k_check` and is the only list `diagram_check` reads. |
| `quiz.json` | judgment (Opus) | `{version, items:[{id, type, question, key, must_include[], anchors, K}]}`; ids starting `n`/`nav` are navigation questions. Answer-free copy in `quiz_questions.json`. |
| `verify/` | tools + agents | `quiz_ans_t*.json` (persona answers), `quiz_grades.json` (`{t1:{q1:true,…}}`), `quiz_aggregate.json`, `provenance_claims.json`, screenshots `i.png`, `iv.png`, `i_diagrams.png`, verifier/observer reports. |
| `STATE.json` | orchestrator | Optional resume state for `n_lint.py`: `{phases:{name:{status: todo\|running\|pass\|fail\|circuit, round, artifacts[], gates[], note}}, next}`. |
| `diagrams/` | `render_diagram.py` | `<id>.svg`. |
| `index.html ii.html i.html iii.html iv.html` | tools only | Rendered pages. Never hand-edit. |
| `_legacy/` | — | Retired artifacts; not linked from the hub. |

## 4. Global files

| Path | Role |
|---|---|
| `matrix/links/candidates.json` | `link_candidates.py` output: `{cards:[{id, run, k, headline, point, title}], candidates:[{a, b, score, shared:[≤6 words], kept?}]}`. Card text = `point`×2 + its anchor paragraphs; Chinese char bigrams + Latin words, TF-IDF cosine; top 3 per card in other runs (ranked over all cards, then pairs across genealogies dropped), score ≥0.05. Already-judged pairs are always kept (`kept:true`) so judgments never go stale. |
| `matrix/links/links.json` | Judgment: `{judged_by, links:[{a, b, type: 呼應\|延伸\|實例\|對照\|不同看法, why}], excluded:[{a, b, why}]}`. Every candidate judged exactly once. Exclusions are published on the page, so their `why` must be specific. |
| `matrix/links/batch_<n>.json`, `matrix/links/judged_<n>.json` | Worker batch input/output; merged into `links.json` by the orchestrator. |
| `matrix/vault/<label>/<label> K<n> <headline≤28>.md` | `vault.py` output: Obsidian notes with front matter (場次, 重點, 原文 file:// URI, tags), point, I paragraphs, `[[wikilinks]]` per link with type + why, and anchor links back to `ii.html#pNNNN`. Gitignored, regenerable. Open `matrix/vault` as an Obsidian vault. |
| `matrix/runs/LOG.md` | Append-only run log (rounds, failures, fixes, mechanical vs judgment, time). |
| `vendor/dagre/` | MIT dagre 0.8.5 for diagram layout (installed `--ignore-scripts`). |

---

## 5. Invariants

1. **Anchors everywhere.** Every content unit (card, sentence, diagram node and edge, claim,
   topic, link card) carries ≥1 `pNNNN` that exists in `source.anchors.json`. HTML carries
   them as `data-anchors="p0011 p0012"` and/or `href="…#pNNNN"`. I/IV card anchors ⊆ that
   K's anchor set. `hNNN` aux anchors are allowed only in IV-side data and are never counted
   in K anchors or coverage.
2. **Verbatim source.** II and III reproduce every paragraph byte-equal (after stripping tags
   and `**`), all `##`/`###` headings in order, all images at their cleaned.md positions
   (linked read-only by relative path into `sessions/<slug>/…`, never copied).
3. **No external knowledge in content.** Each claim must be found in the paragraph it
   cites. Slide text is not a claim source. 〔錄音不清〕 spans do not exist. Keep the speaker's
   terms (no synonym swaps, no dropping objects/subjects). Titles/headlines are claims too
   and need a quote; `i_angle` is only a hint, never copied as a headline. No added
   causality, universals, or turns absent from the source. Speaker claims/plans in I are
   third-person attributed (他提出／他認為), and hopes are not written as facts.
4. **Beginner glossing ladder (I only).** For a jargon term: (1) the source's own plain
   explanation, anchored; else (2) one 補述 `〔補述：…〕` rendered as `<span class="supp"
   data-term>` — dictionary-style, ≤28 CJK, no digits/years/versions/capabilities/
   comparison/causality/evaluation, removable without changing the claim, ≤1 per card,
   ≤7 per page; else (3) don't use the term. Headlines have zero unexplained jargon.
5. **Audience / aux attribution.** Paragraphs or spans listed in `speakers.json` render as
   「聽眾」 in II/III. A claim quoting audience speech must have `speaker:"audience"` (and
   vice versa). An I/IV unit citing only audience paragraphs must say 「聽眾」. Aux items
   must be `src:"aux"`, cite `hNNN`, and display 「出自講義」/講義 tag.
6. **LLM writes data only; tools render HTML.** Judgment steps write JSON
   (`K.json`, `i.json`, `claims.json`, `diagrams.json`, `iv.json`, `matrix/links/links.json`,
   `quiz.json`, `speakers.json`). Every HTML page is produced by `render_*.py` + `ui.py` +
   `assets/theme.css`. Editing a component changes all four pages. Never hand-edit HTML.
7. **No writes to the session** (§1.1). Phase 6 reads session paths through absolute paths recorded in
   `source.anchors.json`.
8. **Exclusions are public and specific.** IV shows excluded literal-similarity pairs with
   reasons; a reason repeated >3 times is a gate failure.

---

## 6. Shared design system (`matrix/tools/ui.py` + `matrix/tools/assets/theme.css`)

Unify the vocabulary, not the layout: II = linear long read, I = scan cards, III = query &
jump, IV = triage network → pair → take away.

- **Theme** (`theme.css`, injected by `n.py build` as `<style id="n-theme">`): goodedunote
  palette — paper `#fdfbf7`, ink `#2d2a26`, accent `#b34a2f`; serif body (Noto Serif TC
  fallbacks), sans for UI (`.ui`, nav, buttons, tags, refs). Offline, no web fonts.
  Build also remaps legacy GitHub-style colors (`COLOR_MAP` in `n.py`) and injects the
  quadrant nav bar `.n-nav` (brand = `short_title`/`title`, truncated to ~20 display
  width; one pill per existing quadrant page).
- **Font floor 14px.** Scale: body 17 (`--fs-body`), secondary 15 (`--fs-2`), minimum 14
  (`--fs-min`). Applies to all visible text including SVG text after its screen scale.
  Enforced by `ui_check.py` U1.
- **`ui.head()` / `ui.masthead(page, title, lead)`**: shared shell `.n-page` > `header.n-mast`
  with kicker 「象限 R　名稱（軸）」, `h1`, optional `.n-lead`, and `ui.how()`.
- **「這頁怎麼讀」 (`.n-how`, exactly 3 steps, per page, from `ui.HOW`)**:
  - ii: 看目錄，知道這場分幾段 / 照講者的順序讀下去 / 卡住時，去 I 看這段的重點
  - i: 先掃一遍下面的重點清單 / 每張卡看標題、短文和圖解 / 挑一張有興趣的，點「讀原文」深入
  - iii: 反白一句有興趣的話，或從右側挑一個深挖題目 / 寫註記，或帶去 Claude、Google 往外查 / 把查到的貼回註記，對照原文判斷
  - iv: 先看場次網：哪幾場和這場最相關 / 點一個場次，並排比對兩場的重點卡 / 想自由探索就切到卡片圖譜；有興趣的在 Obsidian 開啟
  - hub: 看自己是初學還是熟悉這個主題 / 決定要讀完整還是只看重點 / 點進對應的那一格
- **`.n-card`**: the card component shared by I (`<article>`) and IV (`<section>`):
  `id=K<n> data-k data-anchors`, header `.kn` + `h2`, body, `.go` link row.
- **`.n-index`**: the point list (I's 「重點清單」); links to `#K<n>`.
- **`ui.sup(refs, notes=None, base)` → `sup.n-ref`**: superscript source refs; comma
  separated; `pNNNN` → `<base>#pNNNN`, `hNNN` → `#aux-hNNN`. With `notes` it numbers
  footnotes per page; without, it shows the paragraph id.
- **`ui.tag(kind, text)` → `.n-tag`**: one look for 聽眾 (`aud`), 講義 (`aux`), 值得細讀,
  熟手可略, 可能為聽眾, claim types, topic kinds.
- **`ui.nextbox(page, exists)` → `footer.n-next` 「讀完之後」**: routes by the reader's next
  action, only to pages that exist: ii→I, III; i→II, IV; iii→II, IV; iv→III, II.
- No external scripts or CDN; every page opens from `file://`.

---

## 7. Page specs

### 7.1 `index.html` (`render_hub.py`)
Kicker 「好學生矩陣（四象限學習輔助）」, h1 title, lead (speaker only if set), `how('hub')`,
2×2 grid (axes: 完整（N 段）/ 重點（K 個）; 初學 / 精通), cells link to existing pages; a
missing III shows 「這場沒有做深讀：III 只給正在深讀的場次」, other missing cells 「尚未產出」;
`<details>` list of K (「I 與 IV 共用」); footer link to `published_ii` if set.
Exempt from U2/U3, not from U1/U4.

### 7.2 `ii.html` (`render_ii_iii.py --mode ii`)
Masthead + lead 「講者的原話，一段不漏（N 段）…」 + link to the published notes. Sticky TOC
(`##` sections) + text column ≤720px. Each paragraph `<p id=pNNNN data-sha1>` with a
hidden `.pid`; audience paragraphs class `aud` + 「聽眾」 tag; mixed/uncertain spans wrapped
`.aud-span` (title 聽眾發言 / 可能為聽眾發言). Figures `data-after`/`data-before`. No side rail.

### 7.3 `i.html` (`render_i.py`, then `render_diagram.py` embeds SVGs)
Masthead (h1 = `i.json.title`; lead 「N 個重點，約 M 分鐘。…」 computed), `.n-index`
「重點清單」, one `.n-card` per item in K order: headline, 2–3 paras (gloss inserted after
`gloss.after` or the first occurrence of `gloss.term`), diagram `figure.kdiagram
data-k data-diagram` (SVG `role=img`, title/desc, legend for status: existing = solid,
proposed = dashed + 「提議」, hypothetical = dotted grey + 「假設」), `.go` links
「讀原文：<section>」 to `ii.html#pNNNN` (1–2 self-contained entry paragraphs: first sentence
not a connective/pronoun; prefer where the concept is first explained). Body ≤1,200 CJK
(diagrams, nav, footer, how-to, lead excluded). Diagram rules: ≤9 nodes, ≤12 edges,
node ≤18 CJK, edge label ≤6 CJK; edges only where the source states the relation; same-
paragraph lists are not sequences; loop back-edges only when the speaker says feedback and
are `dashed`; dagre TB layout when >2 nodes (LR for ≤2), hub = radial.

### 7.4 `iii.html` (`render_ii_iii.py --mode iii`; deep-study runs only)
Masthead lead explains select → annotate → take out → paste back; collapsible TOC; full
verbatim text with visible `.pid`; images capped at 300px height. Right rail tabs:
- **我的註記** (`localStorage` key `n.iii.<run>`): selecting text pops `#selbar`
  「註記／問 Claude／Google／複製引文」. Each note card: quote (marked in text as
  `mark.ann-m`), 我的筆記, 查回來的重點, 來源網址, 和講者說法的關係 ∈ 未定／一致／補充／矛盾.
  Export as Markdown; clear all. Notes never write back to source, II, or IV.
- **深挖題目** from `topics.json`, grouped by K (summary shows the I headline), each with
  「標出原文」 and 「問 Claude」.
- **主張** (only if `claims.json`): search box, type filter chips with counts, list items
  `data-type data-anchors` with `sup` refs; 聽眾 tag when `speaker:"audience"`.
- The research brief sent to Claude is built deterministically from quote + paragraph
  context (≤320 chars) + optional note, and asks for sources with URL and date, a verdict
  一致/補充/矛盾, and 「查不到就直接說查不到」. Google gets the first 80 chars.
- `assets/iii.js` injected with `CTX={key,title,speaker,run}`.

### 7.5 `iv.html` (`render_iv.py` + `assets/iv.js`; `main data-view="breadth"`)
Requires `K.json` and global `matrix/links/links.json`. Masthead h1 「這場的重點，和其他場次怎麼連」;
lead computed: card count, other-session count, link count, linked sessions, excluded
count. `window.IV={here, sessions[{run,label,title}], cards[{id,run,k,h}], links[{a,b,t,why}], colors}`.
Three levels, far to near:
1. **場次網 (session ring)** — this session at the center, all others on a ring sorted by
   link count; spoke width/node size = link count; thin chords = links between other
   sessions; zero-link sessions dashed. **Mobile (<600px container): replaced by a list
   sorted by link count with bars.**
2. **兩場對照 (pair view)** — click a session: two columns of cards with connecting lines
   (`.map`, lines hidden ≤820px), plus a list of the pair's links with type and why.
3. **卡片圖譜 (card force graph)** — toggle; Obsidian local-graph style; depth 1
   「直接相連」/ 2 「再往外一層」; layout computed once (500 iterations) then drawn static,
   no animation; color = session; hover shows links, click jumps to the card.
Legend of the five relation colors (呼應 green, 延伸 accent, 實例 purple, 對照 blue,
不同看法 amber). Then one `.n-card` per K: headline, point, 「N 條關聯」, relation list (type
chip, link to `../<run>/iv.html#K<n>`, why) or 「已比對其他 N 場，沒有找到真正相關的重點。」,
「在 Obsidian 開啟這張卡」 (`obsidian://open?path=…vault…`), 「讀這場的原文」. Finally a
`<details>` listing every excluded pair with its reason.
Only sessions with the same `genealogy` enter `IV.sessions`/`cards`/`links`. **Solo genealogy** (no other
session in it): `main` also carries `data-solo="1"`; no ring, pair view, graph, legend or JS; lead 「這場屬於「<族譜>」族譜，
族譜裡目前只有這一場，沒有其他場次可以連。…」; 「這頁怎麼讀」 uses `HOW["iv-solo"]`; cards show headline, point and
「讀這場的原文」 only (no 「0 條關聯」). `k_check` asserts the solo page shows no sessions/relations.

---

## 8. Pipeline

Run order for one session. **D** = deterministic tool; **J** = judgment (LLM writes data,
then the listed gate); **T** = user (or orchestrator) decision.

| # | Step | Kind | Driver | Output | Gate |
|---|---|---|---|---|---|
| 1 | `n.py init <session_dir> <run> [--title --speaker --published --reader-i --reader-iv --genre]` | D | `anchor_source.py`, then `build`, `status` | `source.anchors.json`, `meta.json`, `ii.html`, `index.html` | `views_check`, II verify |
| 2 | Set `meta.label`, `short_title`, genre profile (`domain_identifiers`, `non_content_numbers`, `expert_checklist`) | J/T | — | `meta.json` | — |
| 3 | Aux material (optional, speaker's own only) | D | `anchor_aux.py` | `aux.anchors.json` | — |
| 4 | Speaker attribution (if any Q&A) | J | (no prompt file; SPEC §13 writing rules (speaker attribution, W10)) | `speakers.json` | used by T7, J2, k_check |
| 5 | Draft K | J | `matrix/prompts/worker_k.md` | `K.json` | `k_draft_check` D1–D5 |
| 6 | Confirm K | T | — | `K.json.status` contains 已確認 | — |
| 7 | Claims (deep-study runs only) | J | `matrix/prompts/worker_claims.md` + `_provenance.md` | `claims.json` | `iii_check` T4/T7, `provenance_check --view claims` |
| 8 | I cards | J | `matrix/prompts/worker_i.md` + `_provenance.md` | `i.json` | `k_check` |
| 9 | I diagrams (optional) | J | `matrix/prompts/worker_diagram.md` | `diagrams.json` | `diagram_check` D1–D5 |
| 10 | Topic source (deep-study runs) | J | `matrix/prompts/worker_iv_json.md` | `iv.json` | `iv_check` J1–J6 |
| 11 | Topics | D | `topics.py` (run by `build`) | `topics.json` | — |
| 12 | Cross-session candidates | D | `n.py links` → `link_candidates.py` | `matrix/links/candidates.json` | — |
| 13 | Judge every candidate | J | `matrix/prompts/worker_links.md` (batches) | `matrix/links/judged_<n>.json` → `matrix/links/links.json` | `links_check` L0–L7 |
| 14 | Build pages | D | `n.py build <run>` (or `n.py all`) | all HTML, `matrix/vault/` | — |
| 15 | I comprehension quiz | J | `matrix/prompts/quiz_author.md` (Opus → `quiz.json` + `quiz_questions.json`); `matrix/prompts/quiz_taker.md` (persona, 3 fresh trials t1–t3, reads only `i.html` + questions); `matrix/prompts/quiz_grader.md` (Opus, comprehension items only; navigation is graded mechanically) | `verify/quiz_ans_t*.json`, `verify/quiz_grades.json` | `quiz_aggregate` |
| 16 | Verification | J | `matrix/prompts/verifier.md` (fresh context) ; `matrix/prompts/observer.md` on failure | `verify/verify_*_rN.json`, `observer_roundN.md` | §10 |
| 17 | All gates | D | `n.py check <run>`; `n.py qa` for everything | — | exit code |

`n.py build <run>` does, in order: `topics.py` (if `iv.json`) → II → III (if `claims.json`)
→ I (if `i.json`) → diagrams (if `diagrams.json` and `i.html`) → `vault.py` + `render_iv.py`
(if `matrix/links/links.json` and `K.json`) → `render_hub.py` → `apply_theme`.

`n.py status <run>` prints page presence and the first unfinished judgment step with its
prompt. Note: it lists `claims.json` for every run; for genealogy-only runs, skip it (III
is not produced for them).

Shared prompt rules: `matrix/prompts/_provenance.md` (per-unit provenance: quote first, neighbor-
paragraph trap, keep qualifiers, causal-word whitelist, titles aren't the speaker's words)
applies to every content worker. `matrix/prompts/CHANGELOG.md` records
every prompt change triggered by an observer. `matrix/prompts/_legacy/` is retired.

---

## 9. Gates (rule IDs)

| Tool | Scope | Rules |
|---|---|---|
| `views_check.py <run>` | every run | V1 `cleaned.md` sha1 = anchored sha1; V2 every `[[pNNNN]]`/`#pNNNN` in any run `*.md`/`*.html` exists; V3 (`--coverage f`) every `##` section cited |
| `render_ii_iii.py <run> --mode ii\|iii --verify` | II/III | verbatim N/N paragraphs |
| `iii_check.py <run>` | III | T1 verbatim + paragraph count; T2 h2/h3 equal source order; T3 image count = source, paths exist; T4 claim type ∈ 5 values, ≥8 CJK, substring of an anchor, count ≥ max(20, round(0.3·paras)), every section ≥2, 數字 ≥ max(4, round(0.06·paras)) (count rules only when `claims.json` exists); T5 no `<p>` without `id=pNNNN` in main text; T6 no external script/link; T7 audience attribution of claims |
| `provenance_check.py <run> --view claims` | III claims | FAIL-NUMBER, FAIL-DISPLACED (displaced Latin/number ≥1 or CJK bigram ≥2 within ±3 paragraphs), FAIL-HEADING; WARN-DISPLACED, WARN-HEDGE-DROPPED, WARN-CAUSAL-ADDED → `verify/provenance_claims.json` |
| `k_draft_check.py <run>` | K | D1 5–7 points, K1..Kn; D2 anchors exist, 3–35 each; D3 point non-empty ≤45 CJK; D4 not audience-only; D5 pairwise overlap ≤50% of the smaller set |
| `k_check.py <run>` | I + IV pages | k-same-set (data-k sequence = K order in i.html and iv.html; both must exist); k-anchors (non-empty, ⊆ K anchors incl. ii links; aux only in IV and must exist); audience units say 聽眾; i-length ≤1,200 CJK; jargon-gloss (each term in `jargon.txt` or `matrix/tools/jargon_common.txt` glossed within 40 chars of first use per card; none unexplained in titles); supp-limits (〔補述： prefix, ≤1/card, ≤7/page, ≤30 CJK incl. bracket, no digits); IV breadth: listed relations = data links for this run, ring has spokes; no JS errors; screenshots `verify/i.png`, `verify/iv.png`. (Legacy depth checks `iv_v2_checks` run only for an old non-breadth iv.html without iv.json.) |
| `diagram_check.py <run>` | I diagrams | D1 ≤9 nodes, ≤12 edges, type ∈ flow/loop/hub/chain; D2 every node/edge anchored ⊆ K, note has note_anchors, status ∈ existing/proposed/hypothetical; D3 node ≤18 CJK, edge label ≤6 CJK, jargon WARN; D4 embedded in the right card, SVG role=img; D5 Playwright: no JS errors, no overflow; screenshot |
| `iv_check.py <run>` | iv.json | J1 K order, headline/claim/questions present; J2 refs ⊆ K anchors, `hNNN` only with src=aux, audience-only refs need src=audience; J3 quotes are substrings; J4 gaps keys = `expert_checklist`, values 有/原文未提; J5 evidence+questions ≤12, claim ≤120 CJK; J6 lead mentions no `K<n>` |
| `links_check.py` | global | L1 every candidate judged exactly once; L2 no judgment outside candidates; L3 type ∈ 5 values; L4 why present, ≤70 CJK (worker target ≤60); L5 same why used >3 times; L6 near-duplicate whys (bigram Jaccard ≥0.75 with ≥3 others); L7 every run has `meta.genealogy` and no candidate/link/exclusion crosses genealogies; L0 unreadable input. `k_check` also prints WARN jargon-dropped (term in K point missing on card; allowed only under W4a rung 3; silence with `jargon_exempt.txt`). Worker GATE DISPUTE reports go to `matrix/runs/<run>/gate_disputes.md`, surfaced by `n.py status`. |
| `quiz_aggregate.py <run>` | I usefulness | ≥3 trials, median comprehension ≥2/3, navigation success ≥2/3 trials (href pNNNN must be in the question's acceptable anchors — mechanical); interest is reported (`interest_ok`), not gating |
| `ui_check.py <run>` | all pages | U1 visible text ≥14px (SVG scaled); U2 i/ii/iii/iv have 3-step `.n-how`; U3 i/ii/iii/iv use `.n-page .n-mast`; U4 no horizontal overflow at 1280 and 390 |
| `n_lint.py <run>` | resume | re-runs gates of `pass` phases in `STATE.json`; DRIFT if artifacts missing or gates red |

`n.py check <run>` runs: 原文未變動/錨點 (views_check), II 逐字, III 逐字+主張 (if iii.html),
III 主張溯源 (if claims.json), I/IV 重點集合 (if i.html or iv.html), III 深挖題目來源 (iv_check,
if iv.json), IV 跨場次關聯 (links_check, if links.json), I 圖解 (if diagrams.json), I 理解任務
(if `verify/quiz_grades.json`), 版面 (ui_check). Any red → exit 1.

Judgment-level gates (agents, not tools): verifier (unsupported / misattributed /
distorted / wrong_type, stable ids such as `cid`, `data-k`), gloss check for each 補述
(dictionary-only, no speaker claim, correct), field-type, persona quiz.

---

## 10. QAQC loop

Per artifact (each judgment file):

1. **Implement** — a worker (fresh subagent) writes only its data file, following its prompt
   + `_provenance.md`, and runs its own self-check commands.
2. **Check** — run every applicable gate. Any FAIL → return the *specific* failures
   (anchor ids, sentences, card ids) to the same worker.
3. **Review** — gates green → a verifier in a fresh context (sees only the artifact and the
   anchored paragraphs, never the worker's reasoning) lists unsupported/misattributed/
   distorted units → back to the worker.
4. **Observe** — after a failed round, the observer (`matrix/prompts/observer.md`) classifies
   failures (H hallucination / O omission / S spec violation / P prompt defect / R
   checker-or-reference error), finds the root cause, and writes a generalizing prompt
   patch (or a gate fix for R). Prompt changes are logged in `matrix/prompts/CHANGELOG.md`.
5. **Max 3 rounds per artifact** (gates + verifier combined). Still failing after round 3 →
   **circuit-break**: stop, write `matrix/runs/LOG.md`, report to the user, no automatic retry.
6. **All green → the orchestrator re-runs all gates itself** (`n.py check`, `n.py qa`);
   never trust a worker's or verifier's "I checked". Then sign-off (user, or orchestrator when unattended) → next step.
7. Log each round in `matrix/runs/LOG.md`: artifact, round, failures, fix, mechanical vs judgment,
   time. When a structural error is found, codify it into the spec and a gate rather than
   re-checking by eye.

Model roles (see `docs/agents.md`): orchestrator Fable 5.1 (main session); implementer Opus 5.5 for
artifacts that need the strongest writing (quiz author/grader, verifier, links spot-check); content workers
Sonnet 5.5 (worker_k, worker_i, worker_claims, worker_diagram, worker_iv_json, worker_links); link triage
Haiku 5.5; observer Sonnet 5.5 (`matrix/prompts/observer.md`). Substitutions for other CLIs are listed there.

---

## 12. `n.py` subcommands

| Command | Does |
|---|---|
| `n.py init <session_dir> <run> [opts]` | anchor source, write `meta.json`, build, status |
| `n.py build <run>` | deterministic rebuild of one run (§8) |
| `n.py check <run>` | all applicable gates for one run; exit 1 on any red |
| `n.py status <run>` | page presence + next judgment step and its prompt |
| `n.py links` | `link_candidates.py` then `links_check.py` |
| `n.py vault` | export the Obsidian vault (`vault.py`) |
| `n.py qa` | every gate over all runs + links; exit non-zero on any red |
| `n.py all` | `build` every run |

---

## 13. Writing rules (SSoT cited by `matrix/prompts/*.md`; supersedes views_design §V0, §V5, §V8.1/.4/.5/.7/.8, §V0.10)

Section ids below are `§13.x`; the older `§V…` ids appear in parentheses only for traceability.

### 13.1 Common rules (was §V0)

- **W1** A view is disposable; the source is immutable (see §1.3; `views_check` V1 proves it by sha1).
- **W2** Every content block (paragraph, list item, table row, diagram panel, card) carries >=1 anchor `pNNNN`
  that exists in `source.anchors.json` (`data-anchors="p0011 p0012"` and/or `href="…#pNNNN"`).
- **W3** Anchor syntax is fixed: HTML uses `data-anchors` (space-separated) plus `<a href="…#pNNNN">`.
- **W4** No external knowledge. Every claim must be found in the paragraph it cites. Never add definitions,
  numbers, years, or tool versions the speaker did not say.
  - Slide text is not a claim source (a slide may show `91%`; if the speaker did not say it, no view may write it).
  - Spans marked 〔錄音不清〕 are treated as nonexistent: do not guess or fill them in; write only what is
    certain (e.g. 「多了 12（單位不清）」) or omit.
- **W4a Glossing ladder** (only for beginner-reader views: I, II, any narration; III/IV and other expert views
  do not apply it, missing information there is marked 「原文未提」). For a jargon term, in order:
  1. **Source explanation**: the speaker's/cleaned.md's own plain explanation. Treated as a source claim
     (W4/W6 apply), anchored to the paragraph holding the explanation.
  2. **補述 (supplement)** when the source has none: one dictionary-style note, visibly marked
     `〔補述：…〕` (`<span class="supp" data-term="…">`, styled differently from body text).
     - Answers only "what does this word generally mean"; <=28 CJK; must not state what the speaker said or did;
       no digits, years, versions, product capabilities, comparison, causality, or evaluation.
     - Removing it must leave the host sentence's claim unchanged.
     - It is not a claim and needs no anchor, but must sit inside an anchored sentence, with `data-term`
       naming the explained word.
     - Quota per view: I = <=1 per card, <=7 per page. It counts toward the page length cap but not the
       per-sentence cap.
  3. **Don't use the term**: rewrite with the source's plain wording, or drop the sentence (leave it to IV/III).
- **W5 Keep the speaker's terms** (e.g. 穩定層／可替換層, 轉接器 adapters, SDD 堆疊, decision log, harness,
  token, 套件內容檔). Forbidden: swapping in synonyms, or dropping a term's object/subject (「更新 SDD 堆疊」
  → 「更新」; 「差的提示」 → 「含糊的提示」). Words already plain in the source must not be changed to be
  "more colloquial".
- **W5a** Keeping the original term *and* attaching a gloss per W4a is allowed and, in beginner views, required
  for every term.
- **W6** Third-person framing is allowed (「講者指出」) but **never put words in the speaker's mouth**. Text
  inside quotation marks must be a **contiguous substring** of the source.
- **W7** UTF-8; full-width Chinese punctuation; no keys or personal data in files.
- **W8** Provenance headers are filled by tools, never typed by hand.
- **W9 Titles and K fields are not quotations.** Page titles, one-line leads, and card headlines are content
  blocks that need a supporting quote. `K.json` `point` (confirmed, anchored) may serve as the basis;
  `i_angle` (and the retired `iv_angle`) is only a hint and may carry tone absent from the source
  (「為什麼…每次不一樣」「反而更需要」), so it is never copied into a title or sentence. Titles must not
  contain causality, universals, or turns absent from the source.
- **W10 Speaker attribution.** A single-speaker session may contain audience Q&A. `speakers.json` lists only
  non-pure-speaker paragraphs (`audience`/`mixed`/`uncertain`, plus `audience_spans`). II/III tag them 「聽眾」.
  A claim quoting audience speech must have `speaker:"audience"` (`iii_check` T7). An I/IV unit citing only
  audience paragraphs must say 「聽眾」 (`k_check`). Attribute speakers before drafting K; never write an
  audience member's practice as the speaker's advice.

### 13.2 I page (was §V8.1, §V8.4)

- reader = beginner. One `<article data-k>` card per K, in K order; the header also carries `data-anchors`.
- Per card: a headline with zero unexplained jargon and every claim backed by a quote (W9); 2-3 "why care"
  sentences, each <=35 CJK (supplements excluded), the first preferably using the speaker's own analogy;
  terms handled per W4a at their first appearance on that card (each card is self-sufficient); 1-2
  「讀原文」 links to `ii.html#pNNNN`, choosing K-anchored paragraphs that read standalone (first sentence not a
  connective/pronoun; prefer where the concept is first explained or the source gloss lives).
- `data-anchors` = union of the card's unit anchors, and ⊆ that K's anchors.
- No condition details, version numbers, lists, or expert phrasing that needs two or more supplements to
  understand. Whole-page body (including supplements) <=1,200 CJK.
- **Gates** (`k_check`): k-same-set (i and iv `data-k` = K1..Kn same order); k-anchors 100%; i-length <=1,200;
  **jargon-gloss**: every term in `matrix/tools/jargon_common.txt` + the run's `jargon.txt` + K.json proper terms gets
  a 「（…）」 explanation or `class="supp"` within 40 chars of its first appearance in each card, and titles
  have zero unexplained terms (100%; the list is for detection only, prefer over-inclusion);
  **supp-limits**: starts with 「〔補述：」, <=1 per card, <=7 per page, <=28 CJK each (gate counts <=30
  including the bracket), no digits/years/versions, the host sentence still holds after removal (100%);
  **verify-i-supp**: the verifier lists each supplement as a `gloss` unit and checks (a) dictionary-style only,
  (b) states no speaker claim, (c) the definition is correct (0 violations).
- Usefulness is measured by the comprehension quiz (§13.7), not by counting hard sentences.

### 13.3 Genre profile (was §V8.5)

Set per run in `meta.json`: `domain_identifiers` (verifiable domain-specific identifiers, e.g. policy: 危老, URS,
Safety Audit; technical: ports, menu paths, file names, API names — not generic words like MCP or Python);
`non_content_numbers` (numbers or product names that are not content, e.g. election schedule, Autodesk,
Fusion, Claude); `expert_checklist` (items an expert always asks, e.g. 預算、期程、主責局處、法源或制度依據).
`iv.json` `gaps` keys must equal `expert_checklist`, values `有`/`原文未提`; this is a fixed-format check,
not free editorial opinion. Technical sessions may leave the checklist empty. `specific()` matches
`domain_identifiers` first, then discards `non_content_numbers`, then looks at digits/Latin identifiers.

### 13.4 Speaker's auxiliary material (was §V8.7)

The speaker's own handout may be a second source for IV-side data only (`anchor_aux.py` → `aux.anchors.json`,
anchors `hNNN`). Every unit citing it has `src:"aux"` (HTML `data-src="aux"`) and shows 「出自講義」; aux anchors
never count in K anchors or coverage. Material not authored by the speaker must not be used. Where the page
colors quotes, say so (「黃底＝講者原話；標『出自講義』者為講義原文」); a gap check citing the handout also
carries `data-src="aux"` and an `h` anchor. Dedup of counted items is by anchor set; only short names
(quote <=10 chars) in one paragraph merge into one item.

### 13.5 Claims (was §V5)

`claims.json` feeds III (deep-study runs only). `type` ∈ 主張／條件／例外／步驟／數字 (an unconditional general
statement is 「主張」, not 「條件」). `claim` is a contiguous substring of the anchored paragraph (bold markers
stripped); only leading/trailing filler may be dropped (所以、當然、對吧？、再說一次，、你知道的，), never mid-text
edits; length >=8 CJK. Counts and structure are enforced by `iii_check` T4 (§9: count >= max(20, round(0.3·paras)),
each section >=2, 數字 >= max(4, round(0.06·paras))). Each claim row's anchor is clickable and highlights with
`:target`.

### 13.6 Diagrams (was §V8.6)

Draw a diagram only for a K whose source has real order, causality, composition, or route. <=9 nodes, <=12 edges
(rows of <=3 nodes, snaking). Every node and edge carries anchors ⊆ the K. **Arrows are the high-hallucination
zone**: draw one only where the source states the relation; do not turn same-paragraph items into a sequence;
do not put "later" items in a hub with unrelated ones. Every node needs `status` existing (solid) / proposed
(dashed + 「提議」 badge) / hypothetical (dotted grey + 「假設」 badge); emphasis uses border color only, never
fill. A legend is added automatically. Diagram text does not count toward the 1,200 cap.

### 13.7 Comprehension quiz (was §V8.8)

Purpose: measure whether I alone lets a first-time reader understand the talk (replaces the retired
difficult-sentence count, which tracked page length rather than comprehension).
1. Opus authors 3 comprehension questions + 1 navigation question per run into `quiz.json` (answer key,
   `must_include`, anchors); an answer-free copy goes to `quiz_questions.json`.
2. A persona reads only `i.html` + the question file, 3 independent fresh-context trials; trials never see
   each other's answers.
3. An Opus grader grades comprehension items only; navigation is graded mechanically by `quiz_aggregate.py`
   (the answer `href` must be inside the acceptable paragraphs).
- **Threshold**: median comprehension correct >=2/3 and navigation >=2/3 trials. Interest is reported, not gating.
  Questions must be answerable from the I page alone; what the source lacks (timeline, budget, first step)
  cannot be supplied by I and must not be asked.

### 13.8 Acceptance and cross-session links (was §AC, §V8.10-V8.11)

Acceptance = every gate in §9 green plus the verifier and quiz in §10; there is no separate acceptance list.
Cross-session links follow §2 (IV), §4 (`matrix/links/links.json`) and §7.5; the judging worker's rules live in
`matrix/prompts/worker_links.md`. A literal-similarity pair is not a relation (「模型」 CAD vs LLM); every exclusion is
published with a specific reason. A session with no `claims.json` is a genealogy node: I + IV only, never III.
