#!/usr/bin/env python3
"""把所有場次的重點卡匯出成 Obsidian 筆記(確定性)。用法: vault.py
寫 N/vault/<場次標籤>/<K 標題>.md,關聯用 [[雙向連結]],類型與理由照 links/links.json。
筆記只是「一次性衍生物」:每篇都附回到 ii.html 原文的連結,原文以 study 的 cleaned.md 為準。
在 Obsidian 選「開啟資料夾作為 vault」→ 選 N/vault 即可;IV 頁的「在 Obsidian 開啟」會直接跳到該篇。
"""
import json, re
from pathlib import Path

N = Path(__file__).resolve().parent.parent
V = N / "vault"


def note_name(run, k, headline):
    meta = json.loads((N / "runs" / run / "meta.json").read_text(encoding="utf-8"))
    lab = meta.get("label", run)
    h = re.sub(r'[\\/:*?"<>|#^\[\]〔〕]', "", re.sub(r"〔補述：.*?〕", "", headline))[:28]
    return lab, f"{lab} {k} {h}".strip()


def cards():
    out = {}
    for run in sorted((N / "runs").iterdir()):
        if not (run / "K.json").exists(): continue
        I = {x["k"]: x for x in json.loads((run / "i.json").read_text(encoding="utf-8"))["items"]} if (run / "i.json").exists() else {}
        gen = json.loads((run / "meta.json").read_text(encoding="utf-8")).get("genealogy", "")
        for k in json.loads((run / "K.json").read_text(encoding="utf-8"))["K"]:
            h = re.sub(r"〔補述：.*?〕", "", I.get(k["k"], {}).get("headline", k["point"]))
            lab, name = note_name(run.name, k["k"], h)
            out[f"{run.name}#{k['k']}"] = {"run": run.name, "gen": gen, "k": k["k"], "label": lab, "name": name, "headline": h,
                                           "point": k["point"], "anchors": k["anchors"], "i": I.get(k["k"])}
    return out


def main():
    C = cards(); L = json.loads((N / "links/links.json").read_text(encoding="utf-8"))["links"]
    for cid, c in C.items():
        rel = [(x, x["b"] if x["a"] == cid else x["a"]) for x in L if cid in (x["a"], x["b"])]
        ii = (N / "runs" / c["run"] / "ii.html").as_uri()
        body = [f"---\n場次: {c['label']}\n重點: {c['k']}\n原文: {ii}\ntags: [好學生筆記, 四象限]\n---",
                f"# {c['headline']}", "", c["point"], ""]
        if c["i"]:
            body += [p["text"] for p in c["i"]["paras"]] + [""]
        body += ["## 和其他場次的關聯", ""]
        body += [f"- **{x['type']}**　[[{C[o]['name']}]]　{x['why']}" for x, o in rel] or ["- （目前沒有找到其他場次的對應）"]
        body += ["", "## 回到原文", ""] + [f"- [{a}]({ii}#{a})" for a in c["anchors"]]
        p = V / c["label"] / f"{c['name']}.md"; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"vault: {len(C)} notes, {len(L)} links → {V}")


if __name__ == "__main__":
    main()
