#!/usr/bin/env python3
"""IV 廣度:跨場次「重點卡 ↔ 重點卡」候選關聯(確定性,只找候選,不判關係)。
用法: link_candidates.py [--top 3] [--min 0.05]      掃 runs/*/K.json → links/candidates.json
卡片文字 = K.point + 該卡錨點段落原文;中文字元二元組 + 英文詞,TF-IDF 餘弦。
只留同一族譜(meta.json genealogy)內的配對;不同族譜的場次不比對。
字面相似 ≠ 意思相關(例:「參數」CAD 尺寸 vs AI 模型參數量),所以關係類型與排除一律交判斷步驟寫 links/links.json。
"""
import sys, json, re, math, collections
from pathlib import Path

N = Path(__file__).resolve().parent.parent
STOP = set("我們你們他們這個那個就是然後所以因為可以一個什麼的時候其實如果還是已經沒有覺得現在大家")


def toks(t):
    t = t.lower(); out = re.findall(r"[a-z][a-z0-9+#.-]{1,}", t)
    cj = re.sub(r"[^一-鿿]", "", t)
    return out + [cj[i:i + 2] for i in range(len(cj) - 1) if not (cj[i] in STOP and cj[i + 1] in STOP)]


def cards():
    out = []
    for run in sorted((N / "runs").iterdir()):
        kf = run / "K.json"
        if not kf.exists(): continue
        A = {p["id"]: p["text"] for p in json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))["paragraphs"]}
        meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
        I = {}
        if (run / "i.json").exists():
            I = {x["k"]: x["headline"] for x in json.loads((run / "i.json").read_text(encoding="utf-8"))["items"]}
        for k in json.loads(kf.read_text(encoding="utf-8"))["K"]:
            out.append({"id": f'{run.name}#{k["k"]}', "run": run.name, "gen": meta.get("genealogy", ""), "k": k["k"], "point": k["point"],
                        "headline": I.get(k["k"], k["point"]), "title": meta.get("short_title") or meta.get("title", run.name),
                        "text": k["point"] * 2 + " " + " ".join(A[a] for a in k["anchors"] if a in A)})
    return out


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 3
    lo = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 0.05
    C = cards(); tf = [collections.Counter(toks(c["text"])) for c in C]
    df = collections.Counter(); [df.update(set(x)) for x in tf]; n = len(C)
    vec = []
    for x in tf:
        v = {w: c * (math.log((n + 1) / (df[w] + 1)) + 1) for w, c in x.items()}
        z = math.sqrt(sum(a * a for a in v.values())) or 1; vec.append({w: a / z for w, a in v.items()})
    pairs = {}
    for i, a in enumerate(C):
        sc = sorted(((sum(vec[i].get(w, 0) * x for w, x in vec[j].items()), j) for j, b in enumerate(C) if b["run"] != a["run"]), reverse=True)
        for s, j in sc[:top]:
            # 先全庫排名再去掉跨族譜:族譜歸屬改變時,同族譜既有候選不變,不必重判
            if s < lo or C[j]["gen"] != a["gen"]: continue
            key = tuple(sorted((a["id"], C[j]["id"])))
            # 共同詞:給判斷步驟看「為什麼被配對」,也用來抓字面假關聯
            shared = sorted(set(vec[i]) & set(vec[j]), key=lambda w: -(vec[i][w] * vec[j][w]))[:6]
            pairs[key] = {"a": key[0], "b": key[1], "score": round(s, 3), "shared": shared}
    lj = N / "links/links.json"      # 已判過的組一律保留為候選(避免重算後判斷失效)
    if lj.exists():
        J = json.loads(lj.read_text(encoding="utf-8")); gen = {c["id"]: c["gen"] for c in C}
        for x in J["links"] + J["excluded"]:
            key = tuple(sorted((x["a"], x["b"])))
            if key not in pairs and set(key) <= set(gen) and gen[key[0]] == gen[key[1]]:   # 跨族譜的舊判斷不再是候選
                pairs[key] = {"a": key[0], "b": key[1], "score": 0, "shared": [], "kept": True}
    out = {"cards": [{k: c[k] for k in ("id", "run", "k", "headline", "point", "title")} for c in C],
           "candidates": sorted(pairs.values(), key=lambda p: -p["score"])}
    (N / "links").mkdir(exist_ok=True)
    (N / "links/candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"cards={len(C)} runs={len({c['run'] for c in C})} candidates={len(pairs)}")


if __name__ == "__main__":
    main()
