#!/usr/bin/env python3
"""Anchor the paragraphs of a session's cleaned.md (read-only; never writes to the session).

Usage: anchor_source.py <session_dir> <run_dir>
Output: <run_dir>/source.anchors.json
Paragraph split = pipeline/md_parse.parse() (one paragraph = one line), shared with Phase 3.
"""
import sys, json, hashlib, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from pipeline.md_parse import parse  # noqa: E402

IMG = re.compile(r"^!\[.*\]\(.*\)\s*$")


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def build(session_dir):
    md = Path(session_dir) / "cleaned.md"
    h1, subtitle, sections = parse(md)
    paras, n = [], 0
    for sec in sections:
        sub = ""
        for ln in sec["lines"]:
            if ln.startswith("### "):
                sub = ln[4:].strip(); continue
            if IMG.match(ln):
                continue
            n += 1
            paras.append({"id": f"p{n:04d}", "section": sec["title"],
                          "subsection": sub, "text": ln,
                          "sha1": sha1(ln.encode())})
    return {"source": str(md), "source_sha1": sha1(md.read_bytes()),
            "title": h1, "subtitle": subtitle,
            "sections": [s["title"] for s in sections], "paragraphs": paras}


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = build(sys.argv[1])
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    (out / "source.anchors.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(data['paragraphs'])} paragraphs, {len(data['sections'])} sections -> {out/'source.anchors.json'}")


if __name__ == "__main__":
    main()
