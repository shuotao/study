# 好學生筆記 ＋ 好學生矩陣（CLI 版）

把一場演講、會議或課程的錄音，一步一步變成：

**完整逐字稿 → 雙軌字幕 → 好讀的全文 → 名詞補充 → 立場筆記 → 四象限的好學生矩陣**

全程「零省略」：不摘要、不改寫講者的話。所有補充都放在原文旁邊，讀者一眼就分得出哪段是原話、哪段是後加的理解。

> **這個 repo 是 study 專案的一條支線（`cli-edition` 分支）**：從 study 的 git 歷史分出來，只留 CLI 的部分。
> 轉錄、清理、標點、段落、承接、翻譯這些工具，都是 study 已經實跑過很多場的**原版，一個位元都沒改**
> （`docs/upstream.sha1`，測試會檢查）；這個 repo 新加的是串接、閘門、紀錄、查核與矩陣。見 [§12](#12-哪些是原版哪些是新的)。
>
> 這個 repo 來自 2026-10-21 AI Earth Meetup 的分享〈說話與聽話〉（江碩濤）。講稿就放在 `examples/talk-context/`，也是本 repo 的範例素材。
> 簡報第 12–14 頁的流程（Phase 1–6、工具 ■／AI ●／人 • 的分工）就是這裡的程式。

---

## 目錄

0. [三個原則（先讀這個）](#0-三個原則先讀這個)
1. [申請 Groq 帳號與金鑰](#1-申請-groq-帳號與金鑰)
2. [安裝與 /init](#2-安裝與-init)
3. [第一次使用](#3-第一次使用)
4. [六個 Phase 各做什麼](#4-六個-phase-各做什麼)
5. [多個 AI agent 的分工與替換](#5-多個-ai-agent-的分工與替換)
6. [跨 headless：讓 agent 自己跑完](#6-跨-headless讓-agent-自己跑完)
7. [QAQC：事後回查與抓捷徑](#7-qaqc事後回查與抓捷徑)
8. [好學生矩陣怎麼讀](#8-好學生矩陣怎麼讀)
9. [什麼不會被上傳（機敏資料）](#9-什麼不會被上傳機敏資料)
10. [給參加〈說話與聽話〉的讀者](#10-給參加說話與聽話的讀者)
11. [常見問題](#11-常見問題)
12. [哪些是原版，哪些是新的](#12-哪些是原版哪些是新的)

---

## 0. 三個原則（先讀這個）

1. **把任務拆成 phase，每個 phase 只做一件事。** one-shot 請 AI「轉錄＋潤稿」，很容易把「原則上應該可以」潤成「對方同意」。拆開來做，每一步都有明確邊界。
2. **確定性的工作給工具，判斷的工作給 AI，最後的決定給人。** 轉錄、時間軸、全形化、數字數這些交給程式；標點落點、承接語、名詞說明交給 AI；要做到哪一步、人名對不對，由你決定。
3. **每一個 phase 的產物都留下來。** 字幕、全文、筆記都是學習材料。

在這個 repo 裡，這三句話不是口號，而是程式強制的規則：

- 每一步有「閘門（gate）」，沒過就不能進下一步。
- 每一個動作都寫進改不掉的紀錄（`ledger.jsonl`），事後可以回查。

---

## 1. 申請 Groq 帳號與金鑰

語音轉文字用的是 Groq 上的 Whisper large-v3：速度快，而且有免費額度。這是整套流程**唯一需要的 API 金鑰**。其餘的 AI 工作都由你已登入的 AI CLI（Claude Code、Gemini CLI 等）完成，不需要另外的金鑰。

1. 打開 <https://console.groq.com>，用 Google、GitHub 或 Email 註冊並登入。
2. 左側選單點 **API Keys** → **Create API Key**，名稱隨意填（例如 `good-student-notes`）。
3. 畫面上會出現一串 `gsk_` 開頭的金鑰。**它只會顯示一次**，請立刻複製。
4. 在本 repo 根目錄建立 `.env`（`/init` 會幫你從 `.env.example` 複製一份），填入：
   ```
   GROQ_API_KEY=gsk_你的金鑰
   ```
5. 驗證金鑰是否可用：`python3 gsn.py doctor --check-key`

注意事項：

- **免費方案有限制**：有速率限制與每日音訊秒數上限，實際數字以 console 的 **Limits** 頁為準。長音檔會自動切段；遇到 429（太頻繁）時，程式會自動等待重試。
- **多把金鑰輪替**：在 `.env` 加 `GROQ_API_KEY_2=…`、`GROQ_API_KEY_3=…`，被限流時會自動換下一把。
- **金鑰外流時**：到 console 刪掉那把金鑰再重建一把。千萬不要把 `.env` 傳給別人、貼到對話框或放進 git。這個 repo 已設定好擋下這些情況，見 §9。

---

## 2. 安裝與 /init

### 需要的東西

| 項目 | 用途 | 安裝方式 |
|---|---|---|
| Python 3.10+ | 所有工具 | <https://www.python.org> |
| ffmpeg | 切音檔 | macOS：`brew install ffmpeg`<br>Windows：`winget install ffmpeg`<br>Linux：`apt install ffmpeg` |
| 至少一個 AI CLI | 做需要判斷的步驟 | Claude Code／Gemini CLI／Codex CLI／Copilot CLI／Antigravity，擇一即可 |
| （Phase 6）Node.js、Playwright | 矩陣圖解排版與頁面檢查 | `/init` 會幫你裝 |

### 安裝步驟

```bash
git clone https://github.com/shuotao/study.git
cd study
pip install -r requirements.txt
```

接著在 repo 裡打開你的 AI CLI，輸入 **`/init`**。

- Claude Code、Gemini CLI、Antigravity 都有 `/init` 指令；Codex、Copilot 請直接說「run init」。
- 它會執行 `python3 gsn.py doctor --fix`：檢查 Python、ffmpeg、`.env`、Groq 金鑰，並裝好防止機敏資料上傳的 git hook。
- 不用 AI CLI 也可以直接執行：`python3 gsn.py doctor --fix`

> 本 repo 的 `/init` 是「環境設定」，**不會**重寫 `CLAUDE.md`（Claude Code 內建的 `/init` 會被本 repo 的同名 skill 取代）。
>
> macOS 使用者：如果 repo 放在「桌面」或「文件」，第一次執行時系統可能會擋檔案存取。請到「系統設定 → 隱私權與安全性 → 檔案與資料夾（或完整磁碟取用權）」允許你的終端機。

---

## 3. 第一次使用

### 先用範例跑一次（不花 Groq 額度）

```bash
python3 gsn.py new --from-srt examples/talk-context/excerpt.srt \
        --context examples/talk-context/context.txt --slug demo
python3 gsn.py status demo
```

接著在 AI CLI 裡說：「依照 CLAUDE.md，把 demo 這個 session 跑完」。
或用指令 `/good-student-notes demo`（Gemini／Antigravity：`/notes demo`）。

### 處理你自己的錄音

```bash
python3 gsn.py new ~/錄音/講座.m4a \
        --context "講者：王小明（某某公司）；產品：XYZ、ABC；專有名詞：BIM、IFC" \
        --identity 建築師 --terms
```

**`--context` 是最值得花一分鐘寫的東西。** Whisper 對人名、公司名、產品名最常聽錯。把這些寫進去，錯字會少很多；後面的步驟也會拿它來校正名字。

### 主要選項

| 選項 | 作用 |
|---|---|
| `--context "…"` 或 `--context 檔案.txt` | 講者、公司、產品、專有名詞 |
| `--lang zh`（預設）／`--lang en` | 錄音的語言。中文用 study 的 `groq_transcribe.py`，英文用 `groq_transcribe_en.py`。轉錄時**不翻譯** |
| `--no-prompt` | 現場很吵時，Whisper 可能把提示詞吐回來變成假字幕；加這個重轉 |
| `--translate zh-TW` | Phase 2：外語演講加一條繁中字幕軌（雙軌字幕；限 `--lang en`） |
| `--terms` | Phase 4：名詞補充 |
| `--identity 建築師` | Phase 5：用這個立場寫好學生筆記 |
| `--matrix` | Phase 6：好學生矩陣 |
| `--stop-at` | 最多做到哪個 phase（見下表） |

### `--stop-at` 停點

| 指令 | 做到 | 適合 |
|---|---|---|
| `--stop-at p1` | 帶時間軸的逐字稿 `transcript.srt`、`cleaned.srt` | 只要字幕、做剪輯索引 |
| `--stop-at p2` | ＋ 雙軌字幕（需加 `--translate`） | 看外語課程 |
| `--stop-at p3` | ＋ **好讀的全文 `cleaned.md`（預設）** | 大多數人到這裡就夠了 |
| `--stop-at p4` | ＋ 名詞補充 `enhanced.md`（需加 `--terms`） | 主題不熟悉時 |
| `--stop-at p5` | ＋ 立場筆記 `notes_<立場>.md`（需加 `--identity`） | 想用自己的專業吸收 |
| `--stop-at p6` | ＋ 好學生矩陣（需加 `--matrix`） | 想精讀、想串連多場 |

### 日常會用到的指令

```bash
python3 gsn.py status <slug>     # 哪一步在等
python3 gsn.py next <slug>       # 下一步的任務卡（要讀哪份 prompt、輸入輸出是什麼）
python3 gsn.py check <slug>      # 只跑檢查，不改任何東西
python3 gsn.py audit <slug>      # 全部做完後的總查核
```

產物都在 `sessions/<日期>_<檔名>/`，這個資料夾只留在你的電腦上。

---

## 4. 六個 Phase 各做什麼

```
 錄音 ──■ Phase 1 ──▶ transcript.srt（原始證據，永不修改）→ cleaned.srt
           │
           ├─● Phase 2（選）──▶ transcript.zh-TW.srt 繁中字幕軌（外語演講；時間軸由程式鎖住）
           │
           └─● Phase 3 ──▶ cleaned.md 好讀的全文 ＝ 矩陣的第二象限
                 3B 校稿：標點、分段、標題
                 3C 標點：全形化（工具）＋冒號落點（AI）
                 3D 承接：只在句子之間插入承接語
                    │
                    ├─● Phase 4（選）名詞補充 → enhanced.md
                    ├─● Phase 5（選）立場筆記 → notes_<立場>.md
                    └─● Phase 6（選）好學生矩陣 I／II／III／IV
 ■ 工具　● AI（判斷）　每一步之間都有閘門，最後由人確認
```

| Phase | 工具做的（■） | AI 做的（●） | 閘門檢查什麼 |
|---|---|---|---|
| 1 | 切檔、送 Groq、重新對時間、丟幻覺與亂碼、套錯字字典 | — | 時間軸與原始檔逐字相同；被丟掉的字幕要有紀錄 |
| 2 | 拆出純文字、組回字幕、驗時間軸 | 逐條翻譯（看不到時間軸） | 每條都有翻、沒有簡體、時間軸位元相同 |
| 3B | 字數比對、段落長度量測 | 標點、分段（60–120 字）、加標題 | 字數 95–105%、原文片段保留 ≥ 90%、不准出現「講者提到」 |
| 3C | 半形轉全形 | 冒號、引號落點 | 只能改標點，文字一個都不能動 |
| 3D | 只插入的數學證明 | 插入承接語 | 原文必須是新文的子序列、段落數不變 |
| 4／5 | 原文行比對 | 名詞補充、立場類比 | 原文每一行原封不動，新增內容只能在 `>` 區塊 |
| 6 | 錨點、畫頁面、所有頁面檢查 | 重點卡、主張、跨場關聯 | 每個單位都要連回原文段落 `pNNNN` |

規則全文（英文，給 agent 看）：`prompts/rules.md`。

---

## 5. 多個 AI agent 的分工與替換

這個 repo 預設用三種角色互相制衡：**寫的人不改自己的考卷**。

| 角色 | 預設 | 做什麼 | 不做什麼 |
|---|---|---|---|
| **統籌（Orchestrator）** | Fable 5.1（你開的主對話） | 跟你確認要做哪幾步；一次只派一步；**自己重跑檢查**；第 3 次失敗就停下來回報 | 不親手寫被指派給別人的產物 |
| **實作（Implementer）** | Opus 5.5（全文、筆記）<br>Sonnet 5.5（矩陣資料） | 只做任務卡上的那一步，做完執行 `gsn.py done` | 不碰別的步驟、紀錄、檢查程式 |
| **觀察（Observer）** | Sonnet 5.5，全新對話 | 讀紀錄與查核結果，寫 `observer_report.md`，指出有沒有抄捷徑 | 不修改任何產物 |
| **人** | 你 | 提供 context、決定做到哪、確認人名與重點、做最後判斷 | — |

**只有一個 AI CLI 也可以。** 同一個 CLI 輪流扮演三個角色就好，檢查與紀錄照樣有效。觀察那一步請另開一個全新對話。

### 替換表（手邊有什麼就用什麼）

| 角色 | Claude Code | Gemini CLI | Codex CLI | Copilot CLI | Antigravity |
|---|---|---|---|---|---|
| 統籌 | Fable／Opus | Gemini Pro | GPT（高推理） | 任一強模型 | Gemini Pro |
| 實作（全文） | Opus／Sonnet | Gemini Pro | GPT（中） | Sonnet／GPT | Gemini Pro |
| 實作（矩陣） | Sonnet | Gemini Flash | GPT（中） | Sonnet | Gemini Flash |
| 觀察 | Sonnet | Gemini Flash | GPT | Sonnet | Gemini Flash |
| repo 內指令 | `/init` `/good-student-notes` `/observe` | `/init` `/notes` `/observe` | 說「run init」 | 同左 | `/init` `/notes` `/observe` |

所有 CLI 都讀同一份規則：`CLAUDE.md`。`AGENTS.md`、`GEMINI.md` 只有一行 `CLAUDE.md`，負責把 Codex、Copilot、Gemini 指過去。

想換掉某個角色時，只要換掉那一格。不管誰寫的，檢查都一樣嚴格。

每個步驟用哪個模型、多少推理強度（effort）才夠，是實測出來的，結果寫在 `docs/agents.md` §4 與 `docs/qaqc/eval-effort.md`。

---

## 6. 跨 headless：讓 agent 自己跑完

Headless 是指 AI CLI 不開對話視窗、在背景執行一個任務。這裡用的都是 CLI 本身的登入授權，**不需要 API 金鑰**。

```bash
# 用 Claude Code（Sonnet、中等推理）把等待中的步驟一步一步跑完
python3 gsn.py headless <slug> --cli claude --model sonnet --effort medium

# 換成其他 CLI，只差 --cli
python3 gsn.py headless <slug> --cli gemini  --model gemini-2.5-pro
python3 gsn.py headless <slug> --cli codex   --model gpt-5 --effort medium
python3 gsn.py headless <slug> --cli copilot --model claude-sonnet-4.5
python3 gsn.py headless <slug> --cli agy

# 跑到某一步就停
python3 gsn.py headless <slug> --cli claude --until p3-hooks

# 全部跑完後，請一個全新的觀察者寫報告
claude -p "/observe <slug>" --model sonnet
```

（上面 `--model` 的值只是示意，請換成你帳號裡可用的模型名稱。）

運作方式：

- 每一步都開一個全新的 CLI 程序。
- 做完後由程式**自己重跑檢查**，不聽信 agent 說「我檢查過了」。
- 沒過就把確切的錯誤送回去重做；最多 3 輪，然後停下來回報（斷路器）。
- 每一輪的完整對話記錄在 `sessions/<slug>/.gsn/headless/`，給觀察者回查。

> 注意：headless 模式會讓 agent 在 repo 裡自動編輯檔案、執行 python。請只在這個 repo、用你自己的素材執行。

---

## 7. QAQC：事後回查與抓捷徑

AI 最常見的「偷懶」有：跳步驟、一次把三步做完、把冗長段落摘要掉、為了湊字數自己補話、說檢查過其實沒有。這個 repo 用三層來抓。

### 第一層：閘門（每一步）

`gsn.py done` 會重新讀檔檢查，沒過就不放行，等待中的標記（marker）也會留著。

### 第二層：紀錄與總查核（做完後）

每一個動作都寫進 `ledger.jsonl`。每一筆紀錄都帶著前一筆的雜湊值（hash chain），手動改任何一行都會被發現。

`python3 gsn.py audit <slug>` 會逐項檢查：

| 編號 | 檢查 |
|---|---|
| A0 | 紀錄鏈完整，沒有被插入、刪除或修改 |
| A1 | `transcript.srt` 從第一步之後沒被改過 |
| A2／A3 | 每一步都有做、照順序做，而且都經過 `done` |
| A4／A5 | 每一步拿到的輸入，正好是上一步通過檢查的輸出（中間沒被偷改） |
| A6 | 檔案在通過檢查之後沒被再改過 |
| A7 | 用當時凍結的產物，把每一步的檢查重新跑一次 |
| A8 | 每步重做沒超過 3 輪 |

### 字數檢查（QAQC 的核心）

沿用 study 的字數規則：**同口徑比對**（都去空白、排除圖片語法，中文算漢字、英文算字數，E1），
**從原始的全部字幕一路追到最後的產物**（不是只比清理後剩下的，E4），校稿後落在 **95–105%**。

`python3 gsn.py wordcount <slug>` 會印出整條字數鏈（`audit` 的 A9 也會檢查）：

| 階段 | 比對對象 | 標準 |
|---|---|---|
| Phase 1 清理 | 原始全部字幕 | ≥ 90%（低於就提醒：可能清掉了真話） |
| 3B 校稿 | Phase A 文字 | **95–105%** |
| 3C 標點 | 3B 的結果 | 100%（只能動標點） |
| 3D 承接 | 3C 的結果 | 100–112%（只能插入） |
| 4／5 補充、筆記 | 原文本體（扣掉 `>` 區塊） | 100%，另列補充占了多少 |
| 全程 | 原始全部字幕 | 列出最終保留率 |

### 迭代迴圈：log → check → 改進（study 原版 `pipeline_logger.py`）

每一步的檢查結果都會寫進 study 的迭代迴圈：

- `sessions/<slug>/pipeline_log.jsonl` 與 `build/pipeline_runs.jsonl`：每一步一筆紀錄。
- 檢查沒過：自動在 `build/improvement_queue.jsonl` 開一張改進單。
- 同一步之後通過了：自動把那張單關掉。study 原本的迴圈缺了這一步，佇列只會越堆越多，所以這裡補上。
- `python3 gsn.py improve` 列出還沒解決的單，給下一輪處理。如果是規則或檢查本身有問題，交給觀察報告的 S8。

### 第三層：觀察報告

`/observe <slug>` 會產出 `observer_report.md`：

- 給人看的摘要。
- 可信度判定：可信／可信但有註記／不可信。
- 每一步由誰做、重做幾輪、花多久。
- 抓到的捷徑（S1 跳步、S2 合併步驟、S3 手改、S4 摘要、S5 鑽檢查漏洞、S6 謊稱已檢查、S7 動時間軸、S8 規則本身有問題、S9 人名用猜的），每一項都附證據位置。

本 repo 本身也是用這套方式做出來的：建置紀錄、effort 實測、觀察報告都在 `docs/qaqc/`。

---

## 8. 好學生矩陣怎麼讀

同一份全文，依「完整／重點」×「初學／精通」分成四種讀法：

|  | 完整（每一段） | 重點（同一組 5–7 張重點卡） |
|---|---|---|
| **初學** | **II 理解過程**：照講者順序讀完整篇 | **I 建立入口**：先掃重點卡，每張都能點回原文 |
| **精通** | **III 追查與檢核**：反白一句話 → 寫註記 → 帶去 Claude／Google 查 → 把結果貼回來 | **IV 交換與判斷**：這場的重點卡，和同一個「族譜」裡其他場次怎麼連 |

順序建議：**先完整讀一次（II）**，再用重點卡（I）強化，想深入就往下挖（III），累積多場以後才往廣處連（IV）。這正是〈說話與聽話〉第 07–11 頁的主張：沒有完整的脈絡，重點也會變成誤區。

產出位置：`matrix/runs/<slug>/index.html`，直接用瀏覽器打開即可。多場累積後，可以用 `python3 matrix/tools/n.py vault` 匯出成 Obsidian 筆記庫。

規格（英文）：`matrix/SPEC.md`。

---

## 9. 什麼不會被上傳（機敏資料）

`.gitignore` 加上 pre-commit hook（`pipeline/secret_scan.py`），會擋下：

| 不會進 git | 說明 |
|---|---|
| `.env`、任何 `*_API_KEY=…`、`gsk_…`／`sk-…`／`AIza…` 等金鑰、私鑰檔 | 帳單與 API 金鑰 |
| `*.mp3 *.m4a *.wav *.mp4 *.mov …` | 原始音檔與影片，不論放在哪裡 |
| `sessions/` | 你的逐字稿、筆記、紀錄 |
| `matrix/runs/`、`matrix/links/`、`matrix/vault/` | 矩陣產物 |

`/init` 會設定 `git config core.hooksPath .githooks`。之後任何 commit 只要含有上面這些東西，就會被拒絕。

想手動檢查一次：`python3 pipeline/secret_scan.py --all`

> 筆記內容裡的講者姓名、公司等資訊，是否要去識別化、要不要公開，由你在 clone 之後自行決定；這個 repo 不替你處理。它只負責讓**金鑰與原始素材**不會被意外推上去。

---

## 10. 給參加〈說話與聽話〉的讀者

| 簡報頁 | 在 repo 裡 |
|---|---|
| 02–04「這個你們再看看，原則上應該可以」 | Phase 3B 的鐵律：不准把保留語氣潤成同意（`prompts/rules.md` § R2.2） |
| 06 好學生筆記 | Phase 3 的全文 `cleaned.md` |
| 07–11 四象限 | Phase 6 好學生矩陣 |
| 12 Phase 1–2：先守住時間軸 | `.claude/skills/good-student-notes/scripts/groq_transcribe.py`、`scripts/lang/en/srt_zhtw.py` |
| 13 Phase 3：標點就是語境、承接只插在句間 | `prompts/phase3_punct.md`、`prompts/phase3_hooks.md`、`scripts/phase_d_check.py` |
| 14 Phase 4 以後；工具／AI／人的分工 | `prompts/phase4_terms.md`、`prompts/phase5_stance.md`、§5 角色表 |

範例素材：`examples/talk-context/transcript.srt`。這是講稿模擬成「剛轉錄完、沒有標點」的字幕，可以直接拿來跑 Phase 3 以後的每一步：

```bash
python3 gsn.py new --from-srt examples/talk-context/transcript.srt \
        --context examples/talk-context/context.txt --identity 工程師 --matrix
```

---

## 11. 常見問題

**Q：為什麼不一個 prompt 叫 AI 直接產生筆記？**
A：見第 0 節第 1 點。one-shot 為了通順，最常刪掉的正是保留條件與舉例細節。拆開做，每一步都有可以驗證的邊界。

**Q：字數檢查 95–105% 會不會太死？**
A：它只是第一道關卡。真正抓「摘要化」的是「原文 4 字片段保留率 ≥ 90%」，以及後續步驟的「只插入」證明。

**Q：中文以外的語言可以嗎？**
A：可以。轉錄會自動偵測語言，英文會用英文的幻覺規則與字數算法。段落長度 60–120 字的檢查只套用在中文。

**Q：檢查一直不過怎麼辦？**
A：照 `gsn.py done` 印出的 FAIL 逐項修正。同一步失敗 3 次就停下來：通常代表規則或素材有問題，不是再試一次就會好。請看 `observer_report.md` 的 S8，或開 issue。

**Q：逐字稿裡人名錯了怎麼辦？**
A：寫進 `sessions/<slug>/corrections.json`。同一個錯在很多場都出現時，再加到 `dict/typo_dict.<領域>.json`，用 `--domain <領域>` 套用。

---

## 授權

程式碼：MIT（`LICENSE`）。範例講稿〈說話與聽話〉：© 江碩濤，僅供學習本工具使用。

---

## 12. 哪些是原版，哪些是新的

這是 study 的支線，`git log` 看得到完整來歷：

1. 從 study 分出來，刪掉 CLI 以外的部分。
2. 原封不動地匯入 N 的好學生矩陣。
3. 只改路徑，讓矩陣接上這個 repo。
4. 加上新的統籌層。

| 類別 | 內容 | 狀態 |
|---|---|---|
| **study 原版（不改）** | Groq 轉錄（中、英）、Phase A 清理、字典、全形標點、段落長度、承接檢查、簡轉繁、座談歸屬檢查、EN→繁中字幕、迭代迴圈 | 已實跑多場；位元相同，測試鎖住 |
| **N 原版（只改路徑）** | 好學生矩陣的工具與 prompt | 已在 N 實跑 |
| **新的統籌層** | `gsn.py`、閘門、改不掉的紀錄、事後總查核、字數鏈、headless、`/init`、機敏掃描 | 這次新寫，有測試；完整範例跑在 `docs/qaqc/` |
| **新版工具（候選升級）** | 重寫的轉錄、清理、翻譯工具 | 跟原版用同樣的真實資料比較過，結果在 `docs/qaqc/tool-comparison.md`；**只有贏了才會成為預設** |

原版工具要修正時，應該回 study 修，再同步過來；不要只在這裡改。
