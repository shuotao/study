#!/usr/bin/env python3
"""檢查 run 目錄內所有 view 的原文錨點。

用法: views_check.py <run_dir> [--coverage <view.md> ...]
V1 原文 cleaned.md 的 sha1 與錨點建立時一致(原文未被改)
V2 每個 view(*.md / *.html)引用的 [[pNNNN]] / #pNNNN 都存在
V3 --coverage 指定的 view:原文每個 ## 區段至少被引用一次
exit 0 = 全綠;1 = 有失敗
"""
import sys, json, re, hashlib
from pathlib import Path

REF = re.compile(r"\[\[(p\d{4})\]\]|#(p\d{4})\b")


def refs(text):
    return {a or b for a, b in REF.findall(text)}


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    run = Path(args[0])
    cov = args[args.index("--coverage") + 1:] if "--coverage" in args else []
    anchors = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    ids = {p["id"]: p for p in anchors["paragraphs"]}
    fails = []

    cur = hashlib.sha1(Path(anchors["source"]).read_bytes()).hexdigest()
    if cur != anchors["source_sha1"]:
        fails.append(f"V1 原文已變動: {anchors['source']}")

    views = [p for p in run.rglob("*") if p.suffix in (".md", ".html") and p.name != "LOG.md"]
    for v in views:
        bad = sorted(refs(v.read_text(encoding="utf-8")) - ids.keys())
        if bad:
            fails.append(f"V2 {v.name}: 不存在的錨點 {bad}")

    for c in cov:
        used = refs((run / c).read_text(encoding="utf-8")) & ids.keys()
        hit = {ids[i]["section"] for i in used}
        miss = [s for s in anchors["sections"] if s not in hit]
        if miss:
            fails.append(f"V3 {c}: 未覆蓋區段 {miss}")

    print(f"views={len(views)} anchors={len(ids)} coverage_checked={len(cov)}")
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
