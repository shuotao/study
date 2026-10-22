# prompts CHANGELOG (one entry per observer fix)

> Provenance: this changelog is carried over from the private source project (N). "TAO" is the author. New entries go at the bottom.

(Table headers: date | file | version | trigger | key fix. Entries below the header are historical and stay in their original Chinese.)

| Date | File | Version | Trigger | Key fix |
|---|---|---|---|---|
| 2026-10-12 | para_labels.md | v1→v2 | router R1 observer | 判斷順序＋決勝規則 |
| 2026-10-12 | para_labels.md | v2→v3 | router R2 observer | 「示範敘述 vs 一般陳述」核心區分（v2 矯枉過正） |
| 2026-10-12 | matrix/tools/router_v3.json | v3 | router R2 observer | Jev criteria/instructions 凍結；holdout 86.7% 通過 |
| 2026-10-12 | worker_ste.md | v1→v2 | STE 樣本 observer | 逐句溯源、因果詞白名單、保留限定語、中英要點對等 |
| 2026-10-12 | worker_sheet.md | v1→v2 | sheet observer | 每格先引原文、多錨點、標題不是講者的話 |
| 2026-10-12 | _provenance.md | v1 新增 | 跨 view observer | 所有 worker 共用的逐單位溯源程序 |
| 2026-10-12 | worker_claims.md | v1→v1.2 | claims verifier r1–r3 | 加「主張」型、類型決勝規則、穩定 cid |
| 2026-10-12 | verifier.md | v1→v1.1 | claims r1/r2 對錯列 | 用穩定 id 指稱，不用流水號 |
| 2026-10-12 | worker_video.md | v1 新增 | — | 旁白只能取 ste_zh 原句 |
| 2026-10-12 | worker_i.md | v2→v2.1 | 沈伯洋場 persona 中立度 3 | 講者主張一律第三人稱歸屬，承諾不寫成既成事實 |
| 2026-10-12 | worker_diagram.md | v1 新增 | TAO：象限 I 用圖表現流程與關係 | 箭頭需原文關係詞；loop 回邊需講者說回饋 |
| 2026-10-12 | worker_diagram.md | v1→v1.1 | 沈伯洋場 persona+verifier | 節點 status(現況/提議/假設)+圖例;同段並列不畫成先後 |
| 2026-10-12 | worker_iv_json.md | v1 新增 | TAO：IV UI 碎、不像給人看 | LLM 只寫 iv.json；三段短文卡；去掉同意/存疑表單，改為帶走追問清單 |
| 2026-10-13 | prompts converted to English (content rules unchanged) | - | project rule: AI text in English, human text in zh-TW | All active prompts translated; outputs stay zh-TW; tool-matched Chinese strings kept verbatim. New: quiz_author.md, quiz_taker.md, quiz_grader.md (§V8.8). worker_iv_json.md: iv.json now only feeds III topics. |

## Observer 2026-10-13 (root-cause review of the productization loop)
| Date | File | Version | Trigger | Key fix |
|---|---|---|---|---|
| 2026-10-13 | worker_k / worker_i / worker_links / worker_claims / worker_diagram / worker_iv_json | +gate-dispute rule | workers bent content to pass gates (deleted speaker's 「模型」; BES1245/AU4258 workarounds; r5 deleted K1 evidence) | New section "When a gate seems wrong": decide product-vs-gate fault; never change the speaker's words to pass; report `GATE DISPUTE` / `WORKAROUNDS`; never hand-edit derived counts. |
| 2026-10-13 | worker_i.md | +jargon rule | 「模型」 deleted to pass jargon gate | Only valid remedies are gloss or whole-sentence plain rewrite; 模型 term list entry scoped to AI model (CAD model is not a term); check K-point terms still present. |
| 2026-10-13 | worker_links.md | +rule 4, spot-check | judges wrote one generic exclusion reason; recall 0.46-0.64 | Every `why` pair-specific (names concrete things); no one-word variants to dodge L5; second look at exclusions. |
| 2026-10-13 | worker_diagram.md | +legibility floor | I-page diagrams shrank below 14px | Text >= 14px at seen size; shrinking is a content-size signal (split/note), not a font fix. |
