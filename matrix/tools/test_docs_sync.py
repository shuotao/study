#!/usr/bin/env python3
"""Docs-sync gate (AI-facing). Usage: test_docs_sync.py
S1 every tools/*.py, tools/*.cjs (not _legacy) is named in docs/tools.md
S2 every n.py subcommand is named in docs/tools.md, docs/SPEC.md and docs/MANUAL.zh-TW.md
S3 every active prompt (prompts/*.md except CHANGELOG) is named in docs/SPEC.md
S1b every tool named in docs/tools.md exists
S5 docs/model-routing.md link-eval table numbers == eval/links_scores.json (no hand-typed drift)
S4 AI docs English (CLAUDE, SPEC, tools, model-routing < 15% CJK; prompts < 30% — literal zh strings allowed); human docs zh-TW (README, MANUAL > 25%)
"""
import re, sys
from pathlib import Path
N = Path(__file__).resolve().parent.parent; f = []
rd = lambda p: (N / p).read_text(encoding="utf-8") if (N / p).exists() else ""
tools_md, spec, manual = rd("docs/tools.md"), rd("docs/SPEC.md"), rd("docs/MANUAL.zh-TW.md")
for p in sorted(list((N / "tools").glob("*.py")) + list((N / "tools").glob("*.cjs"))):
    if p.name not in tools_md: f.append(f"S1 {p.name} not in docs/tools.md")
for name in sorted(set(re.findall(r"`([\w.-]+\.(?:py|cjs))`", tools_md))):        # S1b 反向:文件列的工具都要存在
    if not ((N / "tools" / name).exists() or (N / "tools/_legacy" / name).exists()): f.append(f"S1b docs/tools.md lists missing tool {name}")
SUB = ["init", "build", "check", "status", "links", "vault", "all", "book", "qa"]
for s in SUB:
    for name, doc in (("docs/tools.md", tools_md), ("docs/SPEC.md", spec), ("docs/MANUAL.zh-TW.md", manual)):
        if not re.search(rf"n\.py\s+{s}\b", doc): f.append(f"S2 `n.py {s}` not in {name}")
for p in sorted((N / "prompts").glob("*.md")):
    if p.name != "CHANGELOG.md" and p.name not in spec: f.append(f"S3 prompt {p.name} not in docs/SPEC.md")
cjk = lambda s: len(re.findall(r"[一-鿿]", s)) / max(1, len(re.sub(r"\s", "", s)))
LANG = [("CLAUDE.md", 0, .15), ("docs/SPEC.md", 0, .15), ("docs/tools.md", 0, .15), ("docs/model-routing.md", 0, .15),
        ("README.md", .25, 1), ("docs/MANUAL.zh-TW.md", .25, 1)] + \
       [(str(p.relative_to(N)), 0, .30) for p in sorted((N / "prompts").glob("*.md"))]   # prompts 英文;可含必要的中文字面字串
for p, lo, hi in LANG:
    r = cjk(rd(p))
    if not rd(p): f.append(f"S4 {p} missing")
    elif not lo <= r <= hi: f.append(f"S4 {p} CJK share {r:.0%} outside {lo:.0%}–{hi:.0%}")
sc = N / "eval/links_scores.json"; mr = rd("docs/model-routing.md")
if sc.exists():
    import json
    S = json.loads(sc.read_text(encoding="utf-8"))
    for model, label in (("haiku", "Haiku"), ("sonnet", "Sonnet"), ("fable", "Fable"), ("jev", "Jev")):
        row = next((l for l in mr.splitlines() if l.startswith(f"| {label}")), "")
        nums = [float(x) for x in re.findall(r"\d\.\d\d", row)]
        want = [S[model][k] for k in ("link_vs_exclude_acc", "link_precision", "link_recall", "type_acc_on_agreed_links")]
        if [round(x, 2) for x in nums[:4]] != [round(x, 2) for x in want]: f.append(f"S5 model-routing {label} row {nums[:4]} != eval {[round(x, 2) for x in want]}")
for x in f: print("FAIL", x)
print("docs sync", "PASS" if not f else f"FAIL {len(f)}"); sys.exit(1 if f else 0)
