#!/usr/bin/env python3
"""md_parse.py — the one paragraph model shared by Phase 3 gates and the Phase 6 matrix.

One paragraph = one non-empty line. `#` = document title, a leading `*...*` line = subtitle,
`##` opens a section, everything before the first `##` is front matter. Ported from study's
md_to_html.parse() so that matrix anchors (pNNNN) are identical to the published reading order.
"""
from pathlib import Path


def parse(md_path):
    """Return (h1, subtitle, sections); sections = [{"title": str, "lines": [str]}]."""
    lines = Path(md_path).read_text(encoding="utf-8").splitlines()
    h1, subtitle, sections, cur = "完整逐字稿", "", [], None
    preamble = []
    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            continue
        if s.startswith("# ") and not s.startswith("## "):
            h1 = s[2:].strip(); continue
        if s.startswith("*") and s.endswith("*") and len(s) > 2 and not subtitle:
            subtitle = s.strip("*").strip(); continue
        if s.startswith("## "):
            cur = {"title": s[3:].strip(), "lines": []}; sections.append(cur); continue
        if cur is None:
            preamble.append(s); continue
        cur["lines"].append(s)
    if not sections and preamble:          # no `##` at all → the whole text is one section
        sections.append({"title": "", "lines": preamble})
    return h1, subtitle, sections
