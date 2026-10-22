#!/usr/bin/env python3
"""zh_parts_check.py — srt_zhtw.py workdir 譯文的機械品質閘。

在 assemble 之前把「能機械證明的」全部證明掉,人眼只留給真正的語感抽查
(memory feedback_mechanical_proof_over_review)。

檢查項:
  C1 覆蓋率     zh_parts 的鍵集合是否等於 segments.json 的存活集
  C2 空值       譯文為空或純標點
  C3 未翻譯     整條仍是英文(拉丁字元比例過高且幾乎無中日韓字)
  C4 術語遵從   來源出現 glossary 詞時,譯文是否含指定譯名
  C5 簡體殘留   逐「字元」偵測(不用 OpenCC 詞組模式 —— s2tw 會把官方術語
                「回路」誤改成「迴路」、s2t 會把「群」改成「羣」)
  C6 加註       譯文出現原文沒有的括號英文註解(零增添)
  C7 長度異常   中文字數 / 英文詞數 比值離群,抓截斷或膨脹

Usage:
  python3 zh_parts_check.py <workdir> [--glossary g.json] [--top 20]
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

CJK = re.compile(r"[一-鿿]")
LATIN = re.compile(r"[A-Za-z]")
PUNCT_ONLY = re.compile(r"^[\s。，、；：？！「」『』（）()\.,;:?!\-—…·]*$")
# 譯文中出現「(全是拉丁字/數字的括號)」= 模型自行加註英文對照
GLOSS_PAREN = re.compile(r"[（(][^）)]*[A-Za-z][^）)]*[）)]")

# OpenCC s2t 會誤報、但台灣正體本來就正確的字形,不列入簡體判定
# OpenCC s2t 會把這些「正體本字」誤判為簡體(它偏好 羣/裏 等異體,且不認得
# 游標/干擾/漏斗 這類本來就用該字的詞)。實測 2026-09-03 逐條人工確認過。
TW_OK = set("群裡台峰冰游干斗只伙")


def load_parts(wd: Path) -> dict[int, str]:
    zh: dict[int, str] = {}
    for p in sorted((wd / "zh_parts").glob("*.json")):
        for k, v in json.loads(p.read_text(encoding="utf-8")).items():
            zh[int(k)] = v
    return zh


def simplified_chars(text: str) -> set[str]:
    """逐字元找簡體專用字:t2s 不變(是簡體字形)且 s2t 有對應正體。"""
    try:
        from opencc import OpenCC
    except ImportError:
        return set()
    s2t, t2s = OpenCC("s2t"), OpenCC("t2s")
    out = set()
    for c in set(text):
        if not CJK.match(c) or c in TW_OK:
            continue
        if t2s.convert(c) == c and s2t.convert(c) != c:
            out.add(c)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--glossary", default=None)
    ap.add_argument("--top", type=int, default=20, help="每項最多列幾筆")
    args = ap.parse_args()

    wd = Path(args.workdir)
    segs = json.loads((wd / "segments.json").read_text(encoding="utf-8"))
    en = {s["i"]: s["en"] for s in segs}
    zh = load_parts(wd)
    drops = set()
    dp = wd / "drops.json"
    if dp.exists():
        drops = set(json.loads(dp.read_text(encoding="utf-8")))
    kept = set(en) - drops
    fails = 0

    # C1 覆蓋率 -------------------------------------------------------
    missing, extra = sorted(kept - set(zh)), sorted(set(zh) - kept)
    print(f"C1 覆蓋率: {len(zh & kept if isinstance(zh, set) else set(zh) & kept)}"
          f"/{len(kept)}  missing={len(missing)} extra={len(extra)}")
    if missing:
        print(f"   缺: {missing[:args.top]}"); fails += 1
    if extra:
        print(f"   多: {extra[:args.top]}"); fails += 1

    # C2 空值 ---------------------------------------------------------
    empties = [i for i, t in zh.items() if not t.strip() or PUNCT_ONLY.match(t)]
    print(f"C2 空/純標點: {len(empties)}")
    if empties:
        print(f"   {empties[:args.top]}"); fails += 1

    # C3 未翻譯 -------------------------------------------------------
    untr = []
    for i, t in zh.items():
        cjk, lat = len(CJK.findall(t)), len(LATIN.findall(t))
        if lat >= 8 and cjk <= 1:
            untr.append(i)
    print(f"C3 疑似未翻譯: {len(untr)}")
    for i in untr[:args.top]:
        print(f"   [{i}] EN: {en[i][:70]}\n        ZH: {zh[i][:70]}")
    if untr:
        fails += 1

    # C4 術語遵從 -----------------------------------------------------
    if args.glossary:
        g = json.loads(Path(args.glossary).read_text(encoding="utf-8"))
        rules = []
        for t in g.get("terms", []):
            # 只查單一明確譯名的詞(含斜線的多選項不強制)
            if "/" in t.get("zh", "") or "/" in t.get("en", ""):
                continue
            rules.append((t["en"].lower(), t["zh"]))
        # 長詞優先:cue 內若已命中更專指的複合詞(panel schedule),
        # 就不要再用泛用詞(schedule)去挑毛病。
        rules.sort(key=lambda r: -len(r[0]))
        ids = sorted(kept & set(zh))
        for tier, pred in (("硬檢(複合詞)", lambda e: " " in e),
                           ("提示(單詞,誤報率高)", lambda e: " " not in e)):
            viol = Counter()
            samples: dict[str, list] = {}
            for i in ids:
                low = en[i].lower()
                # 譯名可能落在相鄰 cue —— 字幕斷在句中時中文語序會把詞挪過去
                win = zh.get(i - 1, "") + zh[i] + zh.get(i + 1, "")
                covered: list[str] = []
                for e, z in rules:
                    if not re.search(rf"\b{re.escape(e)}\b", low):
                        continue
                    if any(e in c for c in covered):
                        continue          # 已被更長的術語涵蓋
                    covered.append(e)
                    if not pred(e) or z in win:
                        continue
                    viol[f"{e} → {z}"] += 1
                    samples.setdefault(f"{e} → {z}", []).append(i)
            print(f"C4 術語未照用 — {tier}: {sum(viol.values())} 次 / {len(viol)} 個詞")
            for k, c in viol.most_common(args.top):
                i = samples[k][0]
                print(f"   {c:4d}x  {k}")
                print(f"          [{i}] EN: {en[i][:60]}")
                print(f"               ZH: {zh[i][:60]}")
    else:
        print("C4 術語遵從: (略過,未給 --glossary)")

    # C5 簡體 ---------------------------------------------------------
    allzh = "".join(zh.values())
    simp = simplified_chars(allzh)
    cnt = Counter(c for c in allzh if c in simp)
    print(f"C5 簡體候選字元: {len(simp)}  (TW_OK 白名單已排除 {sorted(TW_OK)})")
    if simp:
        print(f"   {cnt.most_common(args.top)}")
        for c, _ in cnt.most_common(3):
            hit = next(i for i in zh if c in zh[i])
            print(f"   '{c}' 例 [{hit}]: {zh[hit][:60]}")

    # C6 加註 ---------------------------------------------------------
    glossed = [i for i, t in zh.items()
               if GLOSS_PAREN.search(t) and not GLOSS_PAREN.search(en.get(i, ""))]
    print(f"C6 自行加註英文括號: {len(glossed)}")
    for i in glossed[:args.top]:
        print(f"   [{i}] {zh[i][:70]}")

    # C7 長度異常 -----------------------------------------------------
    out = []
    for i in sorted(kept & set(zh)):
        w = len(en[i].split())
        c = len(CJK.findall(zh[i])) + len(LATIN.findall(zh[i])) / 4
        if w >= 8:
            r = c / w
            if r < 0.45 or r > 2.6:
                out.append((r, i, w, c))
    out.sort()
    print(f"C7 長度比離群(資訊性,跨 cue 斷句會自然造成): {len(out)}")
    for r, i, w, c in (out[:args.top // 2] + out[-args.top // 2:]):
        print(f"   r={r:.2f} [{i}] w={w} c={c:.0f}")
        print(f"        EN: {en[i][:66]}")
        print(f"        ZH: {zh[i][:66]}")

    print(f"\n=== 硬性失敗項(C1/C2/C3): {fails} ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
