#!/usr/bin/env python3
"""translate_srt.py — Phase 2: timeline-locked translation (bilingual subtitles).

The LLM never sees a timecode. The script splits cleaned.srt into a numbered text list, the agent
translates the list into JSON parts, and the script puts the translations back on the ORIGINAL
timecodes and proves they are byte-identical.

  prep     <cleaned.srt> <workdir>            → segments.json, source.txt, parts/ (empty)
  check    <workdir> [--target zh-TW] [--glossary g.json]
           mechanical quality gate on parts/*.json (coverage, empty, untranslated, glossary,
           Simplified characters, added glosses, length outliers); exit 1 on any hard failure
  assemble <workdir> <out_dir> --orig <cleaned.srt> [--target zh-TW]
           → translated.<target>.srt + bilingual.srt; verifies every timecode byte-for-byte

parts/*.json: each file is {"<i>": "<translation>"}; the key set over all files must equal the
segment ids. drops.json (optional) = [ids] judged to be semantic hallucinations; they are left out.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.common import CJK_RE, parse_srt  # noqa: E402

LATIN = re.compile(r"[A-Za-z]")
PUNCT_ONLY = re.compile(r"^[\s。，、；：？！「」『』（）()\.,;:?!\-—…·]*$")
ADDED_GLOSS = re.compile(r"[（(][^）)]*[A-Za-z][^）)]*[）)]")
TW_OK = set("群裡台峰冰游干斗只伙")   # Taiwan-correct glyphs OpenCC misreports as Simplified


def load_parts(wd: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    for p in sorted((wd / "parts").glob("*.json")):
        for k, v in json.loads(p.read_text(encoding="utf-8")).items():
            out[int(k)] = v
    return out


def cmd_prep(srt: Path, wd: Path) -> int:
    blocks = parse_srt(srt.read_text(encoding="utf-8"))
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "parts").mkdir(exist_ok=True)
    segs = [{"i": n, "tc": b["timecode"], "src": " ".join(b["text"].split("\n"))} for n, b in enumerate(blocks, 1)]
    (wd / "segments.json").write_text(json.dumps(segs, ensure_ascii=False, indent=0), encoding="utf-8")
    (wd / "source.txt").write_text("".join(f"{s['i']}\t{s['src']}\n" for s in segs), encoding="utf-8")
    print(f"[p2 prep] {len(segs)} cues → {wd}/source.txt ; write translations to {wd}/parts/*.json")
    return 0


def simplified(text: str) -> set[str]:
    try:
        from opencc import OpenCC
    except ImportError:
        return set()
    s2t, t2s = OpenCC("s2t"), OpenCC("t2s")
    return {c for c in set(text) if CJK_RE.match(c) and c not in TW_OK
            and t2s.convert(c) == c and s2t.convert(c) != c}


def cmd_check(wd: Path, target: str, glossary: Path | None) -> int:
    segs = {s["i"]: s for s in json.loads((wd / "segments.json").read_text(encoding="utf-8"))}
    drops = set(json.loads((wd / "drops.json").read_text())) if (wd / "drops.json").exists() else set()
    tr = load_parts(wd)
    want = set(segs) - drops
    hard, warn = [], []
    missing, extra = sorted(want - set(tr)), sorted(set(tr) - want)
    if missing:
        hard.append(f"C1 coverage: {len(missing)} untranslated ids, e.g. {missing[:10]}")
    if extra:
        hard.append(f"C1 coverage: {len(extra)} ids not in segments or dropped, e.g. {extra[:10]}")
    zh = target.lower().startswith("zh")
    gl = json.loads(glossary.read_text(encoding="utf-8")) if glossary and glossary.exists() else {}
    ratios = []
    for i, t in sorted(tr.items()):
        src = segs.get(i, {}).get("src", "")
        if not t.strip() or PUNCT_ONLY.match(t):
            hard.append(f"C2 empty translation at {i}")
            continue
        if zh and not CJK_RE.search(t) and len(LATIN.findall(t)) > 3:
            hard.append(f"C3 untranslated at {i}: {t[:50]}")
        if not zh and len(CJK_RE.findall(t)) > 2 and target.lower()[:2] not in ("ja", "ko"):
            hard.append(f"C3 untranslated (Han characters left) at {i}: {t[:50]}")
        for term, want_tr in gl.items():
            if term.lower() in src.lower() and want_tr not in t:
                hard.append(f"C4 glossary at {i}: '{term}' should be '{want_tr}'")
        if zh:
            sc = simplified(t)
            if sc:
                hard.append(f"C5 Simplified characters at {i}: {''.join(sorted(sc))}")
        if ADDED_GLOSS.search(t) and not ADDED_GLOSS.search(src):
            warn.append(f"C6 added gloss at {i}: {t[:50]}")
        if zh:
            words = max(1, len(LATIN.findall(src)) // 4 + len(CJK_RE.findall(src)))
            ratios.append((len(CJK_RE.findall(t)) / words, i))
    if ratios:
        rs = sorted(r for r, _ in ratios)
        med = rs[len(rs) // 2]
        for r, i in ratios:
            if med and (r > 3 * med or r < med / 3):
                warn.append(f"C7 length outlier at {i} (ratio {r:.2f} vs median {med:.2f})")
    for h in hard[:40]:
        print("FAIL", h)
    for w in warn[:20]:
        print("WARN", w)
    print(f"[p2 check] {len(tr)}/{len(want)} translated; {len(hard)} hard failure(s), {len(warn)} warning(s)")
    return 1 if hard else 0


def cmd_assemble(wd: Path, out_dir: Path, orig: Path, target: str) -> int:
    segs = json.loads((wd / "segments.json").read_text(encoding="utf-8"))
    drops = set(json.loads((wd / "drops.json").read_text())) if (wd / "drops.json").exists() else set()
    tr = load_parts(wd)
    keep = [s for s in segs if s["i"] not in drops]
    if any(s["i"] not in tr for s in keep):
        print("[p2 assemble] FATAL: translations incomplete — run `check` first", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    one = "\n".join(f"{n}\n{s['tc']}\n{tr[s['i']].strip()}\n" for n, s in enumerate(keep, 1))
    two = "\n".join(f"{n}\n{s['tc']}\n{s['src']}\n{tr[s['i']].strip()}\n" for n, s in enumerate(keep, 1))
    p1, p2 = out_dir / f"translated.{target}.srt", out_dir / "bilingual.srt"
    p1.write_text(one, encoding="utf-8")
    p2.write_text(two, encoding="utf-8")
    orig_tcs = {b["timecode"] for b in parse_srt(orig.read_text(encoding="utf-8"))}
    for path in (p1, p2):
        got = parse_srt(path.read_text(encoding="utf-8"))
        if len(got) != len(keep):
            print(f"[p2 verify] FATAL: {path.name} has {len(got)} cues, expected {len(keep)}", file=sys.stderr)
            return 3
        bad = [(s["i"], s["tc"], g["timecode"]) for s, g in zip(keep, got)
               if g["timecode"] != s["tc"] or g["timecode"] not in orig_tcs]
        if bad:
            print(f"[p2 verify] FATAL: {len(bad)} timecode mismatch(es) in {path.name}: {bad[:5]}", file=sys.stderr)
            return 4
    print(f"[p2 assemble] {len(keep)} cues → {p1.name}, {p2.name}; all timecodes byte-identical to {orig.name}"
          f" ({len(drops)} dropped)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep"); p.add_argument("srt"); p.add_argument("workdir")
    c = sub.add_parser("check"); c.add_argument("workdir"); c.add_argument("--target", default="zh-TW")
    c.add_argument("--glossary")
    a = sub.add_parser("assemble"); a.add_argument("workdir"); a.add_argument("out_dir")
    a.add_argument("--orig", required=True); a.add_argument("--target", default="zh-TW")
    x = ap.parse_args()
    if x.cmd == "prep":
        return cmd_prep(Path(x.srt), Path(x.workdir))
    if x.cmd == "check":
        return cmd_check(Path(x.workdir), x.target, Path(x.glossary) if x.glossary else None)
    return cmd_assemble(Path(x.workdir), Path(x.out_dir), Path(x.orig), x.target)


if __name__ == "__main__":
    sys.exit(main())
