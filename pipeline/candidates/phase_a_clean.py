#!/usr/bin/env python3
"""phase_a_clean.py — candidate Phase A cleaner. SUPERSEDED (2026-10-22, round 2): study fixed SRT/qaqc_srt.py
upstream and the fixed original ties or beats this file on every metric (docs/qaqc/tool-comparison.md).
Kept only to re-run the comparison; gsn.py uses it only with --phase-a candidate.

History: it was the default after it won the head-to-head on 4 real study sessions (docs/qaqc/tool-comparison.md): same dictionaries
and garble thresholds as qaqc_srt.py, but (1) short replies (對／好／了解) are kept, as qaqc_srt.py's own docstring
says they must be — its code dropped every cue under 3 characters; (2) short all-Latin terms inside a Chinese talk
("Writing is rewriting", "domain knowledge") are no longer dropped as garble; (3) English talks get English
caption-service patterns instead of the CJK prefix list; (4) code-switching cues (「我用 Google 的 Gemini Flash」) are
not dropped by the CJK-ratio rule. `gsn.py new --phase-a upstream` runs qaqc_srt.py instead.

Reads transcript.srt (never modified) and writes cleaned.srt with:
  R1.1 hallucination cues dropped (dict/hallucination_prefixes.json + English caption-service patterns)
  R1.2 garbled cues dropped (thresholds in dict/qaqc_config.json; CJK rules only for CJK sessions)
  R1.3 typo dictionary applied (dict/typo_dict.json + optional dict/typo_dict.<domain>.json)
  R1.4 whitespace normalised
  R1.5 timecodes untouched (byte-identical)
Optional: --s2t converts Simplified-drift characters to Taiwan Traditional (OpenCC s2tw, glyphs only).

It also writes echo_report.json: cues where >= 4 context terms appear together, the signature of
Whisper echoing the prompt (a prefix grep alone misses tail echoes). A non-empty report means
"re-transcribe with --no-prompt"; gsn.py shows it as a warning on p1-clean.

Usage:
    python3 pipeline/candidates/phase_a_clean.py <transcript.srt> <cleaned.srt> [--domain NAME] [--context FILE] [--s2t]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dict.load import load_hallucination_prefixes, load_qaqc_config, load_strip_prefixes, load_typo_dict  # noqa: E402
from pipeline.common import format_srt, is_cjk_text, parse_srt  # noqa: E402

_CJK_RE = re.compile(r"[一-鿿㐀-䶿豈-﫿　-〿＀-￯，。！?、;:「」『』(()《》〈〉—…·~]")
_EXOTIC_RE = re.compile(r"[Ⴀ-ჿ؀-ۿЀ-ӿ฀-๿ऀ-ॿ]")
_LONG_LATIN_RE = re.compile(r"(?:[a-zA-Z]{2,}\s+){5,}")
_CFG = load_qaqc_config()
_NOISE_RE = re.compile(r"[" + re.escape(_CFG.get("noise_chars", "┌┐└┘├┤┬┴┼│─")) + r"]")

# English / caption-service hallucinations (Whisper was trained on captioned video)
_EN_HALL = [re.compile(p, re.I) for p in (
    r"^subtitles by\b", r"\bamara\.org\b", r"^thank(s| you) for watching\b", r"^please subscribe\b",
    r"^the end\.?$", r"^[\s.\-—]*$", r"^\(.*(music|applause|laughter).*\)$", r"^\[.*(music|applause|laughter).*\]$",
    r"^key terms\b", r"^terms:", r"^end of transcript\b", r"\btranscription by\b", r"\bcc by\b", r"^captions? by\b")]
_SHORT_TERM_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .'’+#/&\-]*")
_NONLATIN_RE = re.compile(r"[Ѐ-ӿ぀-ヿ一-鿿가-힯؀-ۿ]")


def is_garbled_cjk(text: str) -> bool:
    """R1.2 for CJK sessions. Single-character replies (對／好) are valid and are NOT dropped here."""
    non_space = len(re.sub(r"\s", "", text))
    if non_space == 0:
        return True
    # A short all-Latin cue in a Chinese talk is usually a real term ("domain knowledge", "Claude Code"),
    # not noise; only caption-service hallucinations or long Latin runs are dropped.
    if _SHORT_TERM_RE.fullmatch(text.strip()) and len(text.split()) <= 5:
        return any(rx.search(text.strip()) for rx in _EN_HALL)
    # Code-switching ("我用 Google 的 Gemini Flash"): Chinese plus real Latin words is speech, not garble.
    # The ratio rule is for symbol soup and foreign-script runs; those are still caught below.
    rest = _CJK_RE.sub("", text)
    if len(_CJK_RE.findall(text)) and _SHORT_TERM_RE.fullmatch(re.sub(r"\s+", " ", rest).strip() or "a") \
            and "\ufffd" not in text and not _EXOTIC_RE.search(text) and len(_NOISE_RE.findall(text)) <= _CFG.get("noise_char_max", 1):
        return False
    ratio = len(_CJK_RE.findall(text)) / non_space
    if ratio < _CFG.get("cjk_ratio_min", 0.25) and non_space > _CFG.get("min_chars_for_ratio_check", 10):
        return True
    if "�" in text or len(_NOISE_RE.findall(text)) > _CFG.get("noise_char_max", 1) or _EXOTIC_RE.search(text):
        return True
    return bool(_LONG_LATIN_RE.search(text) and ratio < _CFG.get("long_latin_cjk_ratio_max", 0.5))


def is_garbled_latin(text: str) -> bool:
    """R1.2 for non-CJK sessions: another script inside a Latin-script talk is a hallucination.
    Latin-1 accents (ä/é/ñ) are normal names and are not matched."""
    t = text.strip()
    if any(rx.search(t) for rx in _EN_HALL) or _NONLATIN_RE.search(t):
        return True
    nonspace = re.sub(r"\s", "", t)
    return len(nonspace) > 8 and len(re.findall(r"[A-Za-zÀ-ÿ]", t)) / len(nonspace) < 0.5


def clean(blocks, typo, prefixes, strip_prefixes, cjk: bool):
    st = {"original": len(blocks), "dropped_empty": 0, "dropped_hallucination": 0, "dropped_garbled": 0,
          "typo_hits": 0, "wrapper_stripped": 0, "dropped": []}
    out = []
    for b in blocks:
        text = re.sub(r" {2,}", " ", b["text"].strip())
        for wrong, right in typo.items():
            if wrong in text:
                st["typo_hits"] += text.count(wrong)
                text = text.replace(wrong, right)
        reason = None
        if not text:
            reason = "empty"
        elif cjk and any(text.startswith(p) for p in prefixes):   # the prefix list is written for CJK talks
            reason = "hallucination"
        else:
            for sp in sorted(strip_prefixes, key=len, reverse=True):
                if text.startswith(sp):
                    text = text[len(sp):].lstrip(" ,，。.")
                    st["wrapper_stripped"] += 1
                    break
            if cjk and len(text) < 1:
                reason = "empty"
            elif (is_garbled_cjk(text) if cjk else is_garbled_latin(text)):
                reason = "garbled"
        if reason:
            st[f"dropped_{reason}"] += 1
            st["dropped"].append({"timecode": b["timecode"], "text": b["text"][:80], "reason": reason})
            continue
        out.append({"timecode": b["timecode"], "text": text})
    st["surviving"] = len(out)
    return out, st


def echo_scan(blocks, context: str, min_hits: int = 4):
    terms = {t for t in re.split(r"[\s,，、;；:：/|。.()（）]+", context) if len(t) >= 2}
    hits = []
    for b in blocks:
        n = sum(1 for t in terms if t in b["text"])
        if n >= min_hits:
            hits.append({"timecode": b["timecode"], "hits": n, "text": b["text"][:120]})
    return hits


def s2t(text: str) -> str:
    try:
        import opencc
    except ImportError:
        sys.exit("[phase-a] --s2t needs opencc: pip install opencc-python-reimplemented")
    keep = frozenset("台只了面")   # already-correct Taiwan forms that OpenCC would change
    out = opencc.OpenCC("s2tw").convert(text)
    if len(out) != len(text):
        sys.exit("[phase-a] s2tw changed the text length; refusing (glyph-only conversion expected)")
    return "".join(a if a in keep else b for a, b in zip(text, out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("srt_in")
    ap.add_argument("srt_out")
    ap.add_argument("--domain")
    ap.add_argument("--context")
    ap.add_argument("--s2t", action="store_true")
    a = ap.parse_args()
    src, dst = Path(a.srt_in), Path(a.srt_out)
    if src.resolve() == dst.resolve():
        sys.exit("[phase-a] refusing to overwrite the input: transcript.srt is immutable")
    blocks = parse_srt(src.read_text(encoding="utf-8"))
    cjk = is_cjk_text(" ".join(b["text"] for b in blocks))
    out, st = clean(blocks, load_typo_dict(a.domain), load_hallucination_prefixes(), load_strip_prefixes(), cjk)
    if a.s2t:
        out = [{"timecode": b["timecode"], "text": s2t(b["text"])} for b in out]
    dst.write_text(format_srt(out), encoding="utf-8")
    ctx = Path(a.context).read_text(encoding="utf-8") if a.context and Path(a.context).is_file() else ""
    echoes = echo_scan(out, ctx) if ctx.strip() else []
    report = {"cjk": cjk, "stats": {k: v for k, v in st.items() if k != "dropped"}, "dropped": st["dropped"],
              "prompt_echo_suspects": echoes}
    (dst.parent / "phase_a_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[phase-a] {st['original']} → {st['surviving']} cues (empty {st['dropped_empty']}, "
          f"hallucination {st['dropped_hallucination']}, garbled {st['dropped_garbled']}; "
          f"typo fixes {st['typo_hits']}); prompt-echo suspects {len(echoes)}; cjk={cjk}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
