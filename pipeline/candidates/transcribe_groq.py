#!/usr/bin/env python3
"""transcribe_groq.py — Phase 1: media → SRT with Groq Whisper (large-v3).

FFmpeg cuts the audio into chunks, each chunk goes to Groq, segments are re-timed with the
chunk offset and written as SRT. The output is the session's immutable evidence file.

Design notes (each one is a past incident):
  * Language is AUTO-DETECTED by default. Forcing `zh` on English audio makes Whisper emit a
    Chinese/English salad. Translation is Phase 2, never here.
  * The prompt is neutral and capped at 896 *characters* (Groq counts characters, not bytes).
  * In noisy rooms Whisper echoes the prompt back as fake cues. `--no-prompt` (or
    GROQ_NO_PROMPT=1) sends no prompt at all; `--chunk-seconds 300` reduces loops.
  * Resumable: each finished chunk is cached as JSON in <out_dir>/.groq_chunks/; a re-run skips
    finished chunks. A chunk that fails after all retries aborts the run (no silent 10-minute holes).
  * Several keys may be listed as GROQ_API_KEY, GROQ_API_KEY_2, ... in .env; they rotate on 429/401.

Usage:
    python3 pipeline/transcribe_groq.py <media> <out.srt> [--context FILE] [--lang auto|zh|en|ja|…]
                                        [--no-prompt] [--chunk-seconds 600]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.common import REPO  # noqa: E402

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
PROMPT_MAX_CHARS = 896


def load_keys() -> list[str]:
    """Read GROQ_API_KEY* from the repo .env at the point of use (values may change between runs)."""
    keys = []
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip().startswith("GROQ_API_KEY") and v.strip():
                    keys.append(v.strip().strip('"').strip("'"))
    for k, v in os.environ.items():
        if k.startswith("GROQ_API_KEY") and v:
            keys.append(v)
    return list(dict.fromkeys(keys))


def build_prompt(context: str, lang: str) -> str:
    """Neutral prompt: never claims a language unless the user forced one."""
    context = " ".join(context.split())
    if not context:
        return ""
    head = {"zh": "繁體中文。專有名詞：", "ja": "専門用語：", "en": "Terms: "}.get(lang, "")
    return (head + context)[:PROMPT_MAX_CHARS]


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_audio(media: Path, work: Path, chunk_seconds: int) -> list[Path]:
    existing = sorted(work.glob("chunk_*.mp3"))
    if existing:
        return existing
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(media), "-vn", "-ar", "16000", "-ac", "1",
           "-b:a", "64k", "-f", "segment", "-segment_time", str(chunk_seconds), str(work / "chunk_%03d.mp3")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[groq] ffmpeg failed: {r.stderr[-400:]}")
    return sorted(work.glob("chunk_*.mp3"))


def transcribe_chunk(path: Path, keys: list[str], ki: int, prompt: str, lang: str) -> tuple[dict | None, int]:
    """Retry policy: 429 → next key with linear backoff; 5xx/network → exponential backoff then rotate;
    401 → skip that key; any other 4xx is fatal for the chunk."""
    import requests
    data = {"model": "whisper-large-v3", "response_format": "verbose_json", "temperature": "0.0"}
    if lang != "auto":
        data["language"] = lang
    if prompt:
        data["prompt"] = prompt
    rl = srv = bad = 0
    while True:
        key = keys[ki % len(keys)]
        try:
            with path.open("rb") as f:
                r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, data=data,
                                  files={"file": (path.name, f, "audio/mpeg")}, timeout=300)
            status = r.status_code
        except requests.exceptions.RequestException as e:
            r, status = None, -1
            print(f"  [network] {e}", file=sys.stderr)
        if status == 200:
            return r.json(), ki
        if status == 429:
            rl += 1
            if rl > 2 * len(keys):
                print("  [groq] rate-limit retries exhausted", file=sys.stderr)
                return None, ki
            ki += 1
            wait = min(10 * rl, 60)
            print(f"  [429] rotate to key #{ki % len(keys) + 1}, wait {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if status == -1 or 500 <= status < 600:
            srv += 1
            if srv > 3 * max(1, len(keys)):
                return None, ki
            if srv % 3 == 0:
                ki += 1
            time.sleep(2 ** min(srv, 4))
            continue
        if status == 401:
            bad += 1
            if bad >= len(keys):
                print("  [groq] 401: every key was rejected — check .env", file=sys.stderr)
                return None, ki
            ki += 1
            continue
        print(f"  [groq] HTTP {status} (fatal): {r.text[:300] if r is not None else ''}", file=sys.stderr)
        return None, ki


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("media")
    ap.add_argument("out_srt")
    ap.add_argument("--context", help="context file (speaker names, product names, key terms)")
    ap.add_argument("--lang", default="auto", help="auto (default) or an ISO-639-1 code to force")
    ap.add_argument("--no-prompt", action="store_true", default=os.environ.get("GROQ_NO_PROMPT", "") not in ("", "0"))
    ap.add_argument("--chunk-seconds", type=int, default=int(os.environ.get("GROQ_CHUNK_SECONDS") or 600))
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("[groq] ffmpeg not found — run `python3 gsn.py doctor`")
    keys = load_keys()
    if not keys:
        sys.exit("[groq] no GROQ_API_KEY in .env — see README §1 (Groq 帳號申請)")
    media, out = Path(a.media).resolve(), Path(a.out_srt)
    work = out.parent / ".groq_chunks"
    work.mkdir(parents=True, exist_ok=True)

    ctx = Path(a.context).read_text(encoding="utf-8") if a.context and Path(a.context).is_file() else ""
    prompt = "" if a.no_prompt else build_prompt(ctx, a.lang)
    print(f"[groq] {len(keys)} key(s); lang={a.lang}; prompt={len(prompt)} chars; chunk={a.chunk_seconds}s")

    chunks = split_audio(media, work, a.chunk_seconds)
    print(f"[groq] {len(chunks)} chunk(s)")
    ki, failed, blocks, langs = 0, [], [], set()
    for i, ch in enumerate(chunks):
        cache = ch.with_suffix(".json")
        if cache.exists():
            res = json.loads(cache.read_text(encoding="utf-8"))
            print(f"[groq] chunk {i + 1}/{len(chunks)} cached")
        else:
            print(f"[groq] chunk {i + 1}/{len(chunks)} …")
            res, ki = transcribe_chunk(ch, keys, ki, prompt, a.lang)
            if res is None:
                failed.append(i + 1)
                continue
            cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        langs.add(res.get("language", ""))
        offset = i * a.chunk_seconds
        for seg in res.get("segments", []):
            text = seg.get("text", "").strip()
            if text:
                blocks.append(f"{srt_time(seg['start'] + offset)} --> {srt_time(seg['end'] + offset)}\n{text}")
    if failed:
        print(f"[groq] FATAL: chunk(s) {failed} failed; finished chunks are cached — re-run to resume.",
              file=sys.stderr)
        return 2
    out.write_text("\n".join(f"{n}\n{b}\n" for n, b in enumerate(blocks, 1)), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print(f"[groq] wrote {len(blocks)} cues → {out} (detected language: {', '.join(sorted(l for l in langs if l)) or '?'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
