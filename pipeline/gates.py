"""gates.py — the mechanical gate for every stage (prompts/rules.md is the rulebook, this is the referee).

Each gate returns a list of results {"name", "ok", "detail", "level"} where level is "fail" or "warn".
A stage passes when no result with level "fail" is false. Gates never trust an agent's claim: they
re-read the files. `gsn.py done` runs them before a marker may be cleared; `audit.py` runs all of
them again at the end.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from pipeline.common import (CJK_RE, REPO, content_units, is_cjk_text, load_meta, parse_srt, srt_text)

PY = sys.executable
TOOLS = REPO / "scripts"                      # field-proven study tools, unchanged (docs/upstream.sha1)
SRT_ZHTW = TOOLS / "lang/en/srt_zhtw.py"
ZH_PARTS_CHECK = TOOLS / "lang/en/zh_parts_check.py"

# Third-person summary phrases the integrator must never add (rules.md R2.2). A phrase that already occurs
# in the base text is the speaker's own words (E2) — only NEW occurrences fail.
SUMMARY_PHRASES = ["講者提到", "講者介紹", "講者表示", "講者說明", "講者指出", "本段討論", "本段介紹", "第一部分討論",
                   "接著討論", "這段主要", "總結來說，講者", "the speaker mentions", "the speaker explains",
                   "the speaker discusses", "this section discusses", "in summary, the speaker"]
TIMECODE_RE = re.compile(r"\d{2}:\d{2}:\d{2}[,.]\d{3}")
PUNCT_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def R(name, ok, detail="", level="fail", only_on_fail=False):
    return {"name": name, "ok": bool(ok), "detail": "" if (only_on_fail and ok) else detail, "level": level}


def _rel(a):
    """Repo-relative paths in tool calls, so gate output (and therefore the ledger) never records local folders."""
    try:
        return str(Path(a).resolve().relative_to(REPO)) if isinstance(a, Path) else str(a)
    except ValueError:
        return str(a)


def run_tool(*args) -> tuple[int, str]:
    r = subprocess.run([PY, *map(_rel, args)], cwd=REPO, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def passed(results) -> bool:
    return all(r["ok"] for r in results if r["level"] == "fail")


def core(text: str) -> str:
    """Content characters only: letters/digits/Han, no punctuation, no whitespace, no markdown markers."""
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    return PUNCT_RE.sub("", text.replace("**", ""))


def ngram_retention(base: str, out: str, n: int = 4) -> float:
    """Share of the base's content n-grams that survive in the output (catches summarising/paraphrase)."""
    b, o = core(base), core(out)
    grams = {b[i:i + n] for i in range(max(0, len(b) - n + 1))}
    if not grams:
        return 1.0
    have = {o[i:i + n] for i in range(max(0, len(o) - n + 1))}
    return len(grams & have) / len(grams)


def strip_blockquotes(text: str) -> str:
    """Remove every `>` block (supplements, stance blocks) and return the remaining body."""
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))


def inserted_only(src: str, out: str) -> tuple[bool, str]:
    """Proof for Phases 4-5: every non-blank source line appears unchanged and in order in the output, and every
    line the output adds is inside a `>` block. Returns (ok, reason)."""
    s = [l.rstrip() for l in src.splitlines() if l.strip()]
    o = [l.rstrip() for l in out.splitlines() if l.strip()]
    i = 0
    for line in o:
        if i < len(s) and line == s[i]:
            i += 1
        elif not line.lstrip().startswith(">"):
            return False, f"added or edited non-quote line: {line[:60]}"
    if i < len(s):
        return False, f"source line missing or edited: {s[i][:60]}"
    return True, ""


def body_paragraphs(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.strip()]


def new_phrases(base: str, out: str) -> list[str]:
    return [p for p in SUMMARY_PHRASES if out.lower().count(p.lower()) > base.lower().count(p.lower())]


# ─── stage gates ───

def gate_p1_transcribe(sdir: Path, **_):
    t = sdir / "transcript.srt"
    cues = parse_srt(t.read_text(encoding="utf-8")) if t.exists() else []
    return [R("transcript.srt exists", t.exists()), R("transcript has cues", len(cues) > 0, f"{len(cues)} cues")]


def echo_suspects(blocks, context: str, min_hits: int = 4) -> list[dict]:
    """Prompt-echo scan (study gotcha 7): a cue carrying >= 4 context terms at once is Whisper replaying the prompt.
    A prefix grep misses tail echoes, so count term hits per cue."""
    terms = {x for x in re.split(r"[\s,，、;；:：/|。.()（）]+", context) if len(x) >= 2}
    out = []
    for b in blocks:
        n = sum(1 for x in terms if x in b["text"])
        if n >= min_hits:
            out.append({"timecode": b["timecode"], "hits": n, "text": b["text"][:80]})
    return out


def gate_p1_clean(sdir: Path, **_):
    t, c = sdir / "transcript.srt", sdir / "cleaned.srt"
    if not c.exists():
        return [R("cleaned.srt exists", False)]
    orig = parse_srt(t.read_text(encoding="utf-8"))
    cl = parse_srt(c.read_text(encoding="utf-8"))
    tcs = {b["timecode"] for b in orig}
    bad = [b["timecode"] for b in cl if b["timecode"] not in tcs]
    keep = len(cl) / max(1, len(orig))
    cjk = is_cjk_text(" ".join(b["text"] for b in orig))
    u_orig = content_units("\n".join(b["text"] for b in orig), cjk)
    u_cl = content_units("\n".join(b["text"] for b in cl), cjk)
    ctx = (sdir / "context.txt").read_text(encoding="utf-8") if (sdir / "context.txt").exists() else ""
    echo = echo_suspects(cl, ctx) if ctx.strip() else []
    return [R("timecodes byte-identical to transcript.srt", not bad, f"{len(bad)} foreign timecodes", only_on_fail=True),
            R("word count E4: Phase A keeps >= 90% of ALL original content", u_cl / max(1, u_orig) >= 0.90,
              f"{u_cl}/{u_orig} = {u_cl / max(1, u_orig):.3f}; cues {len(cl)}/{len(orig)} ({keep:.1%})", "warn"),
            R("no prompt-echo suspects", not echo,
              f"{len(echo)} cue(s) with >=4 context terms — re-transcribe with --no-prompt (README §3)", "warn", True)]


def gate_p2_translate(sdir: Path, **_):
    """study srt_zhtw.py + zh_parts_check.py, unchanged: quality gate, then assemble with byte-level timecode proof."""
    wd = sdir / "p2"
    g = ["--glossary", sdir / "glossary.json"] if (sdir / "glossary.json").exists() else []
    rc, out = run_tool(ZH_PARTS_CHECK, wd, *g)
    tail = " | ".join(l.strip() for l in out.splitlines()[-3:])
    res = [R("zh_parts_check C1-C7 (coverage, empty, untranslated, glossary, Simplified, glosses, length)", rc == 0, tail)]
    if rc == 0:
        rc2, out2 = run_tool(SRT_ZHTW, "assemble", wd, sdir / "transcript.zh-TW.srt", "--orig", sdir / "cleaned.srt")
        res.append(R("srt_zhtw assemble: every timecode byte-identical", rc2 == 0 and "COMPLETE" in out2,
                     " | ".join(l.strip() for l in out2.splitlines()[-2:])))
    return res


def gate_p3_polish(sdir: Path, base: Path, **_):
    md = sdir / "cleaned.md"
    if not md.exists():
        return [R("cleaned.md exists", False)]
    b, o = base.read_text(encoding="utf-8"), md.read_text(encoding="utf-8")
    cjk = is_cjk_text(b)
    ub, uo = content_units(b, cjk), content_units(o, cjk)
    ratio = uo / max(1, ub)
    ret = ngram_retention(b, o)
    heads = re.findall(r"^#{2,3} ", o, flags=re.M)
    res = [R("zero omission: content 95%-105% of Phase A text (same basis)", 0.95 <= ratio <= 1.05,
             f"{uo}/{ub} = {ratio:.3f} ({'Han chars' if cjk else 'words'})"),
           R("verbatim retention: >= 90% of source 4-grams survive", ret >= 0.90, f"{ret:.3f}"),
           R("headings inserted (## / ###)", len(heads) >= 1, f"{len(heads)} headings"),
           R("at most one # title", len(re.findall(r"^# ", o, flags=re.M)) <= 1),
           R("no timecodes in cleaned.md", not TIMECODE_RE.search(o)),
           R("no new third-person summary phrases", not new_phrases(b, o), ", ".join(new_phrases(b, o)))]
    if cjk:
        rc, out = run_tool(TOOLS / "para_len_check.py", md, "--quiet")
        res.append(R("paragraph length 60-120 CJK (shorter rather than longer)", rc == 0,
                     out.splitlines()[-1].strip() if out else ""))
    return res


def gate_p3_punct(sdir: Path, base: Path, **_):
    md = sdir / "cleaned.md"
    b, o = base.read_text(encoding="utf-8"), md.read_text(encoding="utf-8")
    rc, out = run_tool(TOOLS / "normalize_punctuation.py", md, "--check")
    same = core(b) == core(o)
    diff_at = next((i for i, (x, y) in enumerate(zip(core(b), core(o))) if x != y), min(len(core(b)), len(core(o))))
    return [R("full-width: no half-width marks left in CJK lines", rc == 0, out.splitlines()[-1] if out else ""),
            R("only punctuation changed (content characters identical)", same,
              "" if same else f"first difference at content char {diff_at}: …{core(o)[max(0, diff_at - 15):diff_at + 15]}…"),
            R("paragraph count unchanged", len(body_paragraphs(b)) == len(body_paragraphs(o)),
              f"{len(body_paragraphs(b))} -> {len(body_paragraphs(o))}")]


def gate_p3_hooks(sdir: Path, base: Path, **_):
    md = sdir / "cleaned.md"
    rc, out = run_tool(TOOLS / "phase_d_check.py", md, "--base", base)
    rc2, out2 = run_tool(TOOLS / "normalize_punctuation.py", md, "--check")
    grew = content_units(md.read_text(encoding="utf-8")) > content_units(base.read_text(encoding="utf-8"))
    return [R("insert-only proof (1:1 paragraphs, subsequence, growth <= 1.12)", rc == 0,
              " ".join(l.strip() for l in out.splitlines()[-2:]) if out else ""),
            R("still full-width after hooks", rc2 == 0, out2.splitlines()[-1] if out2 else ""),
            R("at least one hook inserted", grew, "content did not grow — Phase D skipped?", "warn", True)]


SUPP_RE = re.compile(r"^>\s*\*\*(專業知識補充|Term note)[:：]\s*(.+?)\*\*", re.M)


def gate_p4_terms(sdir: Path, **_):
    src, out = sdir / "cleaned.md", sdir / "enhanced.md"
    if not out.exists():
        return [R("enhanced.md exists", False)]
    o = out.read_text(encoding="utf-8")
    terms = [m.group(2).strip() for m in SUPP_RE.finditer(o)]
    dup = sorted({t for t in terms if terms.count(t) > 1})
    same, why = inserted_only(src.read_text(encoding="utf-8"), o)
    return [R("source lines unchanged and in order; additions only inside > blocks", same, why),
            R("at least one supplement block", len(terms) >= 1, f"{len(terms)} supplements"),
            R("each term supplemented once (R4.3)", not dup, ", ".join(dup))]


def gate_p5_stance(sdir: Path, **_):
    meta = load_meta(sdir)
    ident = meta.get("identity") or ""
    out = sdir / f"notes_{ident}.md"
    if not ident or not out.exists():
        return [R(f"notes_{ident or '<identity>'}.md exists", False)]
    src = sdir / ("enhanced.md" if (sdir / "enhanced.md").exists() else "cleaned.md")
    o = out.read_text(encoding="utf-8")
    first_h2 = o.find("\n## ")
    stance = len(re.findall(r"^>\s*🎯", o, flags=re.M))
    tail = o.rstrip().splitlines()[-12:]
    same, why = inserted_only(src.read_text(encoding="utf-8"), o)
    return [R(f"{src.name} lines unchanged and in order; additions only inside > blocks", same, why),
            R("📝 learning summary before the first section", "📝" in (o[:first_h2] if first_h2 > 0 else o[:2000])),
            R("💡 core insight at the end", any("💡" in l for l in tail)),
            R("stance blocks present (🎯)", stance >= 1, f"{stance} blocks"),
            R("stance blocks name the identity", ident in o, ident)]


def gate_p6_matrix(sdir: Path, **_):
    run = REPO / "matrix" / "runs" / sdir.name
    n = REPO / "matrix" / "tools" / "n.py"
    if not (run / "source.anchors.json").exists():
        return [R("matrix run initialised", False, f"run `python3 matrix/tools/n.py init {sdir} {sdir.name}`")]
    k = json.loads((run / "K.json").read_text(encoding="utf-8")) if (run / "K.json").exists() else {}
    res = [R("K.json confirmed (status contains 已確認)", "已確認" in k.get("status", ""))]
    for page, why in [("ii.html", "II full text"), ("i.html", "I key-point cards"), ("iii.html", "III deep reading (claims.json)"),
                      ("iv.html", "IV cross-session links")]:
        res.append(R(f"{page} rendered ({why})", (run / page).exists()))
    rc, out = run_tool(n, "check", run)
    res.append(R("n.py check (every matrix gate)", rc == 0, " | ".join(l for l in out.splitlines() if l.startswith("FAIL"))[:300]))
    return res


GATES = {"p1-transcribe": gate_p1_transcribe, "p1-clean": gate_p1_clean, "p2-translate": gate_p2_translate,
         "p3-polish": gate_p3_polish, "p3-punct": gate_p3_punct, "p3-hooks": gate_p3_hooks,
         "p4-terms": gate_p4_terms, "p5-stance": gate_p5_stance, "p6-matrix": gate_p6_matrix}


def run_gate(stage: str, sdir: Path) -> list[dict]:
    base = sdir / ".gsn" / f"{stage}.base"
    return GATES[stage](sdir, base=base)


def phase_a_plaintext(sdir: Path) -> str:
    """Phase 3 input: cleaned.srt without index/timecodes, one cue per line."""
    return srt_text(sdir / "cleaned.srt")


__all__ = ["run_gate", "passed", "GATES", "phase_a_plaintext", "CJK_RE"]
