#!/usr/bin/env python3
"""srt_translate_zhtw.py — 填 srt_zhtw.py workdir 的 zh_parts/(EN cue → zh-TW)。

補上 `srt_zhtw.py` 契約中唯一缺的一環:prep 產出 segments.json / source.txt 後,
本腳本逐批把英文 cue 交給 headless Antigravity(`agy -p`,OAuth 通道,非 API key,
CLAUDE.md 原則 5 + prompts/publish_qaqc.md § S4.5.11),把譯文寫成
`<workdir>/zh_parts/part_NNNNN-NNNNN.json`,再由 `srt_zhtw.py assemble` 組回 SRT
並逐條 byte 驗時間軸。

與 md_translate_zhtw.py 的差異:I/O 契約是 **cue index**(不是 markdown 段落),
所以要求模型回傳 JSON *物件* {"<i>": "<譯文>"},鍵集合必須恰等於本批 index。
字幕會斷在句中,故每批附前後各 --context-window 條「唯讀上下文」幫助判讀,
但譯文仍嚴格 1:1、不跨 cue 搬字(否則 assemble 的時間軸驗證會被架空)。

Usage:
  python3 srt_translate_zhtw.py <workdir> [--glossary g.json] [--model NAME]
                                [--batch 40] [--context-window 3]
                                [--max-consecutive-fails 3] [--limit N]
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash-medium"
# Antigravity 會退役模型(describe_images.py 2026-09-01 教訓):啟動時對 `antigravity models`
# 解析驗證,不在清單就依序降級。
MODEL_PREFERENCE = ("gemini-3.8-flash-medium", "gemini-3.8-flash-low",
                    "gemini-3.7-flash-medium", "gemini-3.7-flash-low",
                    "gemini-3.6-flash-medium", "gemini-3.6-flash-low")
# agy 會間歇性卡死(§ S4.5.11 的節流/空回應樣態)。實測正常批 ~17s,故把單次呼叫
# 壓在 3 分鐘、失敗即重試 —— 之前設 10m 讓兩批各燒掉 24 與 65 分鐘。
PRINT_TIMEOUT = "3m"
CALL_TIMEOUT_S = 200
RETRY_PER_BATCH = 4
RETRY_SLEEP_S = 10


# ---------------------------------------------------------------- model

def resolve_model(want: str) -> str:
    try:
        r = subprocess.run(["antigravity", "models"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return want
        ids, names = set(), set()
        for line in r.stdout.splitlines():
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if not parts:
                continue
            ids.add(parts[0])
            if len(parts) > 1:
                names.add(parts[1])
    except Exception:
        return want
    if want in ids or want in names:
        return want
    for cand in MODEL_PREFERENCE:
        if cand in ids:
            print(f"[translate] model {want!r} 不在清單,降級為 {cand!r}", file=sys.stderr)
            return cand
    flash = sorted(i for i in ids if "flash" in i)
    if flash:
        print(f"[translate] model {want!r} 不在清單,降級為 {flash[0]!r}", file=sys.stderr)
        return flash[0]
    return want


def call_antigravity(prompt: str, model: str) -> str:
    """呼叫 agy,輸出走「檔案」而非 pipe,並在自己的 process group 裡跑。

    2026-09-03 教訓:原本用 subprocess.run(capture_output=True, timeout=…),
    逾時後 Python 會殺掉 agy 本身、然後**不帶 timeout 再讀一次 pipe** 收尾 ——
    agy 留下持有 stdout 的孫程序時,那一讀就永遠回不來,timeout 形同虛設
    (實測單批卡 3,891 秒)。改成檔案重導(pipe 不會滿也不會被孫程序卡住)
    + start_new_session,逾時殺整個 process group。
    """
    cmd = ["antigravity", "-p", prompt, "--model", model,
           "--dangerously-skip-permissions", "--print-timeout", PRINT_TIMEOUT]
    with tempfile.TemporaryDirectory(prefix="agy_") as td:
        o, e = Path(td) / "out.txt", Path(td) / "err.txt"
        with open(o, "wb") as fo, open(e, "wb") as fe:
            proc = subprocess.Popen(cmd, stdout=fo, stderr=fe,
                                    stdin=subprocess.DEVNULL,
                                    start_new_session=True)
            try:
                rc = proc.wait(timeout=CALL_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                raise RuntimeError(f"antigravity timeout >{CALL_TIMEOUT_S}s "
                                   f"(已殺整個 process group)")
        err = e.read_text(encoding="utf-8", errors="replace")
        if rc != 0:
            raise RuntimeError(f"antigravity rc={rc}: {err[:300]}")
        return o.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- glossary

def load_glossary(path: Path | None) -> dict:
    if not path:
        return {"terms": [], "keep_english": [], "ambiguous": [], "suggested": [], "asr_fixes": {}}
    g = json.loads(path.read_text(encoding="utf-8"))
    g.setdefault("terms", [])
    g.setdefault("keep_english", [])
    g.setdefault("ambiguous", [])
    g.setdefault("suggested", [])
    g.setdefault("asr_fixes", {})
    return g


def apply_asr_fixes(text: str, fixes: dict[str, str]) -> str:
    """EN→EN 誤聽修正,只作用在 workdir 的翻譯輸入;transcript.srt 不動(原則 1)。"""
    for wrong, right in fixes.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.IGNORECASE)
    return text


_PROVENANCE = re.compile(r"核對|WebSearch|同上頁|同頁|全頁|curl")


def _hint(note: str) -> str:
    """note 欄混了出處紀錄(curl 逐字核對…)與真正的用法提示,只留後者。"""
    note = (note or "").strip()
    if not note or _PROVENANCE.search(note):
        return ""
    return f"({note[:30]})"


def glossary_block(g: dict, sample: str, full: bool) -> str:
    low = sample.lower()
    lines = []
    keep = g.get("keep_english") or []
    if keep:
        lines.append("【必須保留英文原字串】" + "、".join(keep))
    hits = [t for t in g["terms"]
            if full or t.get("en", "").lower() in low]
    if hits:
        lines.append("【官方/專有名詞繁中譯名 — 出現時必須照用】")
        lines += [f"  {t['en']} → {t['zh']}" + _hint(t.get("note", ""))
                  for t in hits]
    sug = [s for s in g["suggested"]
           if full or s.get("en", "").lower() in low]
    if sug:
        lines.append("【無官方 UI 譯名 — 建議用法,求全篇一致】")
        lines += [f"  {s['en']} → {s['zh']}" for s in sug]
    amb = [a for a in g["ambiguous"]
           if full or a.get("en", "").lower() in low]
    if amb:
        lines.append("【一詞多義 — 依上下文選擇】")
        for a in amb:
            opts = "; ".join(f"{o['zh']}({o.get('context','')})"
                             for o in a.get("zh_options", []))
            lines.append(f"  {a['en']} → {opts}")
    return "\n".join(lines) if lines else "(本批未命中術語表)"


# ---------------------------------------------------------------- prompt

PROMPT = """你是專業繁體中文(台灣)技術譯者,正在翻譯一支 {topic} 的字幕。以下是連續的英文字幕條目,每條有一個編號。

{glossary}

【前文(唯讀,只為理解語境,不要翻譯、不要輸出)】
{before}

【要翻譯的條目(共 {n} 條)】
{payload}

【後文(唯讀,只為理解語境,不要翻譯、不要輸出)】
{after}

規則:
1. 逐條翻譯,忠實完整、零省略零增添。**一條字幕對應一條譯文**,絕不合併、拆分或把
   內容搬到別條 —— 每條譯文必須只涵蓋該條英文的內容。
2. 字幕常斷在句子中間,這是正常的。譯文也照樣斷在對應位置,不要為了通順把下一條的
   內容提前翻出來,也不要補上英文裡沒有的字。
3. 上方術語表列出的譯名必須照用。產品名、軟體 UI 英文名、指令、參數名、檔案格式、縮寫、
   知名 AI / 科技專有名詞保留英文原字串(如 LLM、Prompt、Agent、OpenAI、Tesla、PyTorch、Transformer 等)。
4. 使用台灣業界慣用語與繁體中文,標點使用全形。**絕不可出現簡體字。**
5. 講者的口語填充詞(um, uh, you know, like)可以省略不譯,但實質內容一字不可少。
   **不要加註解**:不可以在譯文中補上原文沒有的括號說明、英文原文對照或譯註
   (例如不可寫成「recent files(近期檔案)」)。該保留英文就只寫英文,該翻譯就只寫中文。
6. 只輸出一個 JSON 物件,鍵是條目編號的字串、值是該條譯文,鍵集合必須**恰好等於**
   上面要翻譯的 {n} 個編號,不多不少。不要輸出任何其他文字或說明。

輸出格式範例:
{{"{first}": "……", "{last}": "……"}}"""


def extract_json_object(raw: str) -> dict:
    t = raw.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t.rstrip())
    # 掃第一個「字串感知的」平衡大括號區段,容忍前後夾雜敘述
    start = t.find("{")
    if start == -1:
        raise json.JSONDecodeError("no JSON object found", t[:80], 0)
    depth, in_str, esc = 0, False, False
    for k in range(start, len(t)):
        c = t[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[start:k + 1])
    raise json.JSONDecodeError("unbalanced JSON object", t[:80], 0)


def translate_batch(batch: list[dict], before: list[dict], after: list[dict],
                    g: dict, model: str, full_gloss: bool,
                    topic: str = "技術教學與演講") -> dict[int, str]:
    payload = "\n".join(f"{s['i']}\t{s['en']}" for s in batch)
    ctx_b = "\n".join(s["en"] for s in before) or "(無)"
    ctx_a = "\n".join(s["en"] for s in after) or "(無)"
    sample = payload + " " + ctx_b + " " + ctx_a
    prompt = PROMPT.format(topic=topic,
                           glossary=glossary_block(g, sample, full_gloss),
                           before=ctx_b, after=ctx_a, payload=payload,
                           n=len(batch), first=batch[0]["i"], last=batch[-1]["i"])
    want = {s["i"] for s in batch}
    last_err = ""
    for attempt in range(1, RETRY_PER_BATCH + 1):
        try:
            raw = call_antigravity(prompt, model)
            obj = extract_json_object(raw)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            print(f"  [batch {batch[0]['i']}-{batch[-1]['i']}] attempt {attempt} "
                  f"fail: {last_err[:160]}", file=sys.stderr)
            time.sleep(RETRY_SLEEP_S)
            continue
        try:
            got = {int(k): str(v).strip() for k, v in obj.items()}
        except (ValueError, TypeError) as e:
            last_err = f"bad keys: {e}"
            time.sleep(RETRY_SLEEP_S)
            continue
        empty = [k for k, v in got.items() if not v]
        if set(got) == want and not empty:
            return got
        missing, extra = sorted(want - set(got)), sorted(set(got) - want)
        last_err = f"misalign missing={missing[:5]} extra={extra[:5]} empty={empty[:5]}"
        print(f"  [batch {batch[0]['i']}-{batch[-1]['i']}] attempt {attempt} "
              f"{last_err}", file=sys.stderr)
        time.sleep(RETRY_SLEEP_S)
    raise RuntimeError(f"batch {batch[0]['i']}-{batch[-1]['i']} failed "
                       f"{RETRY_PER_BATCH}x — {last_err}")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir", help="srt_zhtw.py prep 產生的 workdir")
    ap.add_argument("--glossary", default=None, help="EN→zh-TW 術語表 JSON")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--context-window", type=int, default=3)
    ap.add_argument("--max-consecutive-fails", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0,
                    help="只跑前 N 批(試跑用,0=全部)")
    ap.add_argument("--range", default=None, metavar="LO-HI",
                    help="只處理這段 cue index(可開多個工人跑不相交的區間;"
                         "part 檔以 index 命名,彼此不會覆蓋)")
    ap.add_argument("--full-glossary", action="store_true",
                    help="每批都送完整術語表(預設只送本批命中的詞)")
    ap.add_argument("--topic", default="技術演講與教學",
                    help="影片主題描述(如：Andrej Karpathy 關於 AI、LLM 與 Prompting 的演講)")
    args = ap.parse_args()

    wd = Path(args.workdir)
    seg_path = wd / "segments.json"
    if not seg_path.exists():
        print(f"FATAL: {seg_path} 不存在,請先跑 srt_zhtw.py prep", file=sys.stderr)
        sys.exit(1)
    segments = json.loads(seg_path.read_text(encoding="utf-8"))
    parts_dir = wd / "zh_parts"
    parts_dir.mkdir(exist_ok=True)

    g = load_glossary(Path(args.glossary) if args.glossary else None)
    fixes = g.get("asr_fixes") or {}
    if fixes:
        for s in segments:
            s["en"] = apply_asr_fixes(s["en"], fixes)
        print(f"[translate] 套用 {len(fixes)} 條 ASR 修正(僅作用於 workdir)",
              file=sys.stderr)

    done: set[int] = set()
    for p in parts_dir.glob("*.json"):
        try:
            done |= {int(k) for k in json.loads(p.read_text(encoding="utf-8"))}
        except Exception as e:
            print(f"WARN: 略過壞掉的 part {p.name}: {e}", file=sys.stderr)
    if done:
        print(f"[translate] resume:已完成 {len(done)}/{len(segments)} 條",
              file=sys.stderr)

    model = resolve_model(args.model)
    print(f"[translate] engine=antigravity model={model} batch={args.batch} "
          f"ctx={args.context_window}", file=sys.stderr)

    lo, hi = 1, len(segments)
    if args.range:
        lo, hi = (int(x) for x in args.range.split("-"))
        print(f"[translate] 限定範圍 {lo}-{hi}", file=sys.stderr)

    cw = args.context_window
    consecutive_fails = 0
    failed: list[list[int]] = []
    ran = 0
    for start in range(0, len(segments), args.batch):
        chunk = segments[start:start + args.batch]
        pending = [s for s in chunk if s["i"] not in done and lo <= s["i"] <= hi]
        if not pending:
            continue
        if args.limit and ran >= args.limit:
            print(f"[translate] --limit {args.limit} 到達,停止", file=sys.stderr)
            break
        ran += 1
        before = segments[max(0, start - cw):start]
        after = segments[start + len(chunk):start + len(chunk) + cw]
        try:
            got = translate_batch(pending, before, after, g, model,
                                  args.full_glossary, topic=args.topic)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            failed.append([pending[0]["i"], pending[-1]["i"]])
            consecutive_fails += 1
            if consecutive_fails >= args.max_consecutive_fails:
                (wd / "failed_batches.json").write_text(
                    json.dumps(failed, ensure_ascii=False), encoding="utf-8")
                print(f"FATAL: 連續 {consecutive_fails} 批失敗,熔斷退出。"
                      f"請檢查 antigravity 登入狀態/配額後重跑(可續跑)。",
                      file=sys.stderr)
                sys.exit(2)
            continue
        consecutive_fails = 0
        out = {str(k): got[k] for k in sorted(got)}
        name = f"part_{pending[0]['i']:05d}-{pending[-1]['i']:05d}.json"
        (parts_dir / name).write_text(
            json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
        done |= set(got)
        print(f"[translate] {len(done)}/{len(segments)} cues  -> {name}",
              file=sys.stderr)

    if failed:
        (wd / "failed_batches.json").write_text(
            json.dumps(failed, ensure_ascii=False), encoding="utf-8")
        print(f"WARN: {len(failed)} 批失敗,已記錄 failed_batches.json", file=sys.stderr)
    print(f"OK  {len(done)}/{len(segments)} cues translated -> {parts_dir}")
    sys.exit(0 if len(done) == len(segments) else 1)


if __name__ == "__main__":
    main()
