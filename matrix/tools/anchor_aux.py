#!/usr/bin/env python3
"""為講者自己的輔助材料(官方講義等)產生獨立錨點 hNNN(只讀來源,不寫回)。
用法: anchor_aux.py <run_dir> <aux_file> [--label 講者官方講義]
輸出 <run_dir>/aux.anchors.json:{"source","sha1","label","items":[{"id":"h001","section","text"}]}
規則:aux 錨點只准用在 IV(§V8.7),頁面上必須標「出自講義」;不計入 K 錨點與覆蓋率。
"""
import sys, json, hashlib
from pathlib import Path

run, src = Path(sys.argv[1]), Path(sys.argv[2])
label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "講者輔助材料"
items, sec, n = [], "", 0
for ln in src.read_text(encoding="utf-8").splitlines():
    s = ln.strip()
    if not s: continue
    if s.startswith("#"): sec = s.lstrip("#").strip(); continue
    if s.startswith("(") and "使用者提供" in s: continue
    n += 1; items.append({"id": f"h{n:03d}", "section": sec, "text": s})
(run / "aux.anchors.json").write_text(json.dumps({"source": str(src), "sha1": hashlib.sha1(src.read_bytes()).hexdigest(),
                                                  "label": label, "items": items}, ensure_ascii=False, indent=1))
print(len(items), "aux items ->", run / "aux.anchors.json")
