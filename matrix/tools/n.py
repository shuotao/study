#!/usr/bin/env python3
"""Phase 6 — Good-Student Matrix (好學生矩陣) entry point.

  python3 matrix/tools/n.py init  <session_dir> <run> [--title T] [--speaker S] [--published URL]
                                  [--reader-i R] [--reader-iv R] [--genre tech|policy] [--genealogy G]
        create matrix/runs/<run>/: anchors -> meta.json -> ii.html -> index.html
  python3 matrix/tools/n.py build <run>    deterministic render of ii / iii (if claims.json) / i / diagrams / iv / hub
  python3 matrix/tools/n.py check <run>    every gate that applies to the artifacts present; any red -> exit 1
  python3 matrix/tools/n.py status <run>   page presence + the next judgment step and its prompt
  python3 matrix/tools/n.py links          cross-session candidates -> matrix/links/candidates.json
  python3 matrix/tools/n.py vault          export Obsidian notes -> matrix/vault/
  python3 matrix/tools/n.py all            rebuild every run
  python3 matrix/tools/n.py qa             master gate over all runs + links; must be green before "done"

Judgment steps (LLM) write data files only; tools render every page (spec: matrix/SPEC.md).
K.json (user or orchestrator confirms) -> i.json (+diagrams.json) -> deep-study only: claims.json, iv.json
-> links/links.json (IV) -> quiz. The session's cleaned.md is read-only for the matrix.
"""
import sys, json, re, subprocess
from pathlib import Path

N = Path(__file__).resolve().parent.parent
T = N / "tools"
QUADS = [("index.html", "", "總覽"), ("ii.html", "II", "理解過程"), ("i.html", "I", "建立入口"),
         ("iii.html", "III", "追查與檢核"), ("iv.html", "IV", "交換與判斷")]


def sh(*args, quiet=False):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=N, capture_output=True, text=True)
    if not quiet: print((r.stdout.strip().splitlines() or [""])[-1])
    return r.returncode, r.stdout + r.stderr


def run_dir(name):
    p = Path(name)
    return p if p.is_absolute() or p.exists() else N / "runs" / name


# worker 自寫頁面常用的 GitHub 系配色 → 好學生筆記配色(只改頁面自己的 <style>,冪等)
COLOR_MAP = {"#0b57d0": "#a8442a", "#0b5cad": "#a8442a", "#0969da": "#a8442a", "#0b4fd6": "#a8442a", "#0b3d91": "#7a3a24",
             "#1f2328": "#2d2a26", "#57606a": "#7a7264", "#6b7280": "#7a7264", "#8a8f98": "#7a7264", "#8a8a8a": "#7a7264",
             "#d0d7de": "#e4d8ca", "#e5e2da": "#e4d8ca", "#e6e4dc": "#e4d8ca", "#e6e8eb": "#e4d8ca",
             "#eef1f4": "#f3ebe0", "#f1f3f5": "#f7f1e8", "#fbfaf7": "#fdfbf7", "#fafaf7": "#fdfbf7",
             "#fff3c4": "#fbefe7", "#fff8e1": "#f7f1e8", "#ffe3a3": "#f3dccd", "#e0a800": "#e0a892", "#5c3d00": "#7a3a24", "#7a4b00": "#7a3a24",
             "#f6e3d9": "#fbefe7", "#efd3c4": "#f3dccd",
             "#e3f0ff": "#f3ebe0", "#eef5ff": "#f7f1e8", "#7aa7e6": "#c2683f"}


def remap_colors(t):
    def fix(m):
        css = m.group(1)
        for a, b in COLOR_MAP.items():
            css = re.sub(re.escape(a), b, css, flags=re.I)
        return f"<style>{css}</style>"
    return re.sub(r"<style>(.*?)</style>", fix, t, flags=re.S)


def apply_theme(run):
    css = (T / "assets/theme.css").read_text(encoding="utf-8")
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8")) if (run / "meta.json").exists() else {}
    title = meta.get("short_title") or meta.get("title", "四象限")
    w = lambda s: sum(0.55 if ord(c) < 128 else 1 for c in s)   # 顯示寬度:拉丁字母約半格
    if w(title) > 20:
        while w(title) > 19: title = title[:-1]
        title += "…"
    for f, r, name in QUADS:
        p = run / f
        if not p.exists(): continue
        t = p.read_text(encoding="utf-8")
        t = re.sub(r'<style id="n-theme">.*?</style>', "", t, flags=re.S)
        t = remap_colors(t)
        t = t.replace("</head>", f'<style id="n-theme">{css}</style></head>', 1)
        links = "".join(f'<a class="q{" on" if g == f else ""}" href="{g}"><b>{rr}</b>{nm}</a>'
                        for g, rr, nm in QUADS[1:] if (run / g).exists())
        nav = (f'<nav class="n-nav"><div class="in"><a class="brand" href="index.html">{title}</a>{links}</div></nav>')
        t = re.sub(r'<nav class="n-nav">.*?</nav>', "", t, flags=re.S)
        t = re.sub(r"(<body[^>]*>)", r"\1" + nav.replace("\\", "\\\\"), t, count=1)
        p.write_text(t, encoding="utf-8")


def init(argv):
    src, name = Path(argv[0]).expanduser(), argv[1]
    opt = lambda k, d="": argv[argv.index(k) + 1] if k in argv else d
    run = N / "runs" / name; run.mkdir(parents=True, exist_ok=True)
    sh(T / "anchor_source.py", src, run)
    A = json.loads((run / "source.anchors.json").read_text(encoding="utf-8"))
    mp = run / "meta.json"; meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    meta.update({k: v for k, v in {"title": opt("--title", A["title"]), "speaker": opt("--speaker"), "published_ii": opt("--published"),
                 "reader_i": opt("--reader-i", "第一次接觸這個主題的讀者"), "reader_iv": opt("--reader-iv", "熟悉這個領域的專業者"),
                 "genre": opt("--genre", "tech"), "genealogy": opt("--genealogy", "default"), "storage_key": f"n.iv.{name}"}.items() if v or k not in meta})
    meta.setdefault("domain_identifiers", []); meta.setdefault("non_content_numbers", []); meta.setdefault("expert_checklist", [])
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    build([str(run)]); status([str(run)])


def build(argv, exit_on_fail=True):
    """確定性產生每一頁;任何子步驟失敗都回報並以非零結束(不留舊頁冒充新頁)。"""
    run = run_dir(argv[0]); bad = []
    def step(*args, quiet=False):
        rc, out = sh(*args, quiet=quiet)
        if rc: bad.append((Path(str(args[0])).name, out.strip().splitlines()[-3:]))
    if (run / "iv.json").exists(): step(T / "topics.py", run, quiet=True)        # III 深挖題目(原 IV 的追問)
    step(T / "render_ii_iii.py", run, "--mode", "ii")
    if (run / "claims.json").exists(): step(T / "render_ii_iii.py", run, "--mode", "iii")   # III=深度:只給正在深讀的場次
    if (run / "i.json").exists(): step(T / "render_i.py", run)                       # I 由資料產生(與 IV 同一套元件)
    if (run / "diagrams.json").exists() and (run / "i.html").exists(): step(T / "render_diagram.py", run)
    if (N / "links/links.json").exists() and (run / "K.json").exists():         # IV 廣度:跨場次關聯
        step(T / "vault.py", quiet=True); step(T / "render_iv.py", run)
    step(T / "render_hub.py", run, quiet=True)
    apply_theme(run)
    for name, tail in bad: print("BUILD FAIL", name, *tail, sep="\n  ")
    print("build", "FAILED" if bad else "done" + ":", ", ".join(f for f, _, _ in QUADS if (run / f).exists()))
    if bad and exit_on_fail: sys.exit(1)
    return not bad


def check(argv):
    run = run_dir(argv[0]); rows = []
    plan = [("原文未變動/錨點", True, [T / "views_check.py", run]),
            ("II 逐字", (run / "ii.html").exists(), [T / "render_ii_iii.py", run, "--mode", "ii", "--verify"]),
            ("III 逐字+主張", (run / "iii.html").exists(), [T / "iii_check.py", run]),
            ("III 主張溯源", (run / "claims.json").exists(), [T / "provenance_check.py", run, "--view", "claims"]),
            ("I/IV 重點集合", (run / "i.html").exists() or (run / "iv.html").exists(), [T / "k_check.py", run]),
            ("III 深挖題目來源", (run / "iv.json").exists(), [T / "iv_check.py", run]),
            ("IV 跨場次關聯", (N / "links/links.json").exists(), [T / "links_check.py"]),
            ("I 圖解", (run / "diagrams.json").exists(), [T / "diagram_check.py", run]),
            ("I 理解任務", (run / "verify/quiz_grades.json").exists(), [T / "quiz_aggregate.py", run]),
            ("版面（字級≥14、讀法說明）", True, [T / "ui_check.py", run])]
    bad = 0
    for label, applies, cmd in plan:
        if not applies: rows.append((label, "—", "未產出")); continue
        rc, out = sh(*cmd, quiet=True); bad += rc != 0
        last = [l for l in out.strip().splitlines() if l.strip()][-1:] or [""]
        rows.append((label, "PASS" if rc == 0 else "FAIL", last[0][:70]))
    w = max(len(r[0]) for r in rows)
    for r in rows: print(f"{r[1]:5} {r[0]:<{w}}  {r[2]}")
    sys.exit(1 if bad else 0)


def status(argv):
    run = run_dir(argv[0]); has = lambda f: (run / f).exists()
    K = json.loads((run / "K.json").read_text(encoding="utf-8")) if has("K.json") else None
    steps = [("K.json 重點集合", has("K.json") and "已確認" in K.get("status", ""), "matrix/prompts/worker_k.md → k_draft_check → 交人確認（status 寫「已確認」；無人值守時由 orchestrator 確認並寫 confirmed_by）"),
             ("claims.json（III，只給深讀場次；族譜節點可略）", has("claims.json") or not has("iii.html") and not has("iv.json"), "matrix/prompts/worker_claims.md → 再 n.py build"),
             ("i.json（I）", has("i.json"), "matrix/prompts/worker_i.md → 再 n.py build"),
             ("diagrams.json（I 圖解，可選）", has("diagrams.json"), "matrix/prompts/worker_diagram.md → 再 n.py build"),
             ("III 深挖題目 topics.json（可選）", has("topics.json"), "iv.json 的追問 → matrix/tools/topics.py；或讀者在 III 自己反白開題"),
             ("IV 跨場次關聯 links/links.json", (N / "links/links.json").exists(), "n.py links → 判斷每組候選（關係類型＋理由）→ links_check"),
             ("I 理解任務測驗", has("verify/quiz_grades.json"), "matrix/prompts/quiz_author.md → matrix/prompts/quiz_taker.md ×3 → matrix/prompts/quiz_grader.md → quiz_aggregate.py")]
    print("頁面:", " ".join(f"{r or 'index'}{'✓' if has(f) else '·'}" for f, r, _ in QUADS))
    nxt = None
    for name, done, how in steps:
        print(f"  {'✓' if done else '·'} {name}" + ("" if done else f"  ← {how}"))
        if not done and nxt is None: nxt = name
    gd = run / "gate_disputes.md"                     # worker GATE DISPUTE / WORKAROUNDS reports, written by the orchestrator, await a decision
    if gd.exists() and gd.read_text(encoding="utf-8").strip():
        print("待裁決:", gd.relative_to(N)); nxt = nxt or "裁決 gate_disputes.md"
    print("下一步:", nxt or "全部完成 → n.py check")


def qa():
    rows = []
    for r in sorted((N / "runs").iterdir()) if (N / "runs").exists() else []:
        if not (r / "source.anchors.json").exists(): continue
        p = subprocess.run([sys.executable, str(T / "n.py"), "check", str(r)], cwd=N, capture_output=True, text=True)
        rows.append((f"run {r.name}", p.returncode, [l for l in p.stdout.splitlines() if l.startswith("FAIL")]))
    if (N / "links/links.json").exists():
        p = subprocess.run([sys.executable, str(T / "links_check.py")], cwd=N, capture_output=True, text=True)
        rows.append(("links", p.returncode, [l for l in (p.stdout + p.stderr).splitlines() if "FAIL" in l][:5]))
    bad = 0
    for label, rc, detail in rows:
        print(f"{'PASS' if rc == 0 else 'FAIL'}  {label}"); bad += rc != 0
        for d in detail: print("      ", d[:140])
    print(f"qa: {len(rows) - bad}/{len(rows)} green"); return 1 if bad else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) >= 2 else ""
    if cmd == "links":   # 跨場次候選(之後由判斷步驟寫 links/links.json)
        rc1, _ = sh(T / "link_candidates.py"); rc2, _ = sh(T / "links_check.py"); sys.exit(rc1 or rc2)
    if cmd == "vault":   # 匯出 Obsidian 筆記到 vault/
        rc, _ = sh(T / "vault.py"); sys.exit(rc)
    if cmd == "all":     # 重建每一個 run
        ok = []
        for r in sorted((N / "runs").iterdir()):
            if (r / "source.anchors.json").exists(): print(r.name, end=": "); ok.append(build([str(r)], exit_on_fail=False))
        sys.exit(0 if all(ok) else 1)
    if cmd == "qa":      # master gate: every run + links; any red -> exit 1
        sys.exit(qa())
    if len(sys.argv) < 3 or cmd not in ("init", "build", "check", "status"): sys.exit(__doc__)
    {"init": init, "build": build, "check": check, "status": status}[sys.argv[1]](sys.argv[2:])
