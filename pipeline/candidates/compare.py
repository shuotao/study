#!/usr/bin/env python3
"""compare.py — head-to-head: candidate (rewritten) tools vs the unchanged study tools, on real study sessions.

A candidate becomes the default only if it wins here. Inputs are read from a study checkout (read-only);
nothing is written back. Results → docs/qaqc/tool-comparison.json (the .md is written by hand from it).

  python3 pipeline/candidates/compare.py phase-a     --study ~/Desktop/study
  python3 pipeline/candidates/compare.py transcribe  --study ~/Desktop/study --clip-start 600 --clip-seconds 300
  python3 pipeline/candidates/compare.py translate   --study ~/Desktop/study

Ground truth for Chinese sessions = the session's final cleaned.md (human-proofed and published). A cue counts as
"real speech" when >= 50 % of its 4-grams occur in that text. Phase A: a dropped real-speech cue is a FALSE DROP
(zero-omission loss); a kept cue with < 20 % overlap is a possible kept hallucination (reported, then read).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from pipeline.common import CJK_RE, parse_srt  # noqa: E402

OUT = REPO / "docs/qaqc/tool-comparison.json"
PUNCT = re.compile(r"[\s\W_]+", re.UNICODE)
ZH_SESSIONS = ["2026-07-06_lightalking", "2026-07-22_genai-meetup-1", "2026-07-22_genai-meetup-2",
               "2026-10-19_taipei-current-songshan-xinyi"]
EN_SESSION = "09_15__0600_AS1569"


def core(s: str) -> str:
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"^#+\s*", "", s, flags=re.M)
    return PUNCT.sub("", s.replace("**", "")).lower()


def grams(s: str, n: int = 4) -> set[str]:
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def overlap(text: str, truth_grams: set[str]) -> float:
    g = grams(core(text))
    return len(g & truth_grams) / len(g) if g else 0.0


def save(section: str, data) -> None:
    allr = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    allr[section] = data
    OUT.write_text(json.dumps(allr, ensure_ascii=False, indent=1), encoding="utf-8")


# ─── Phase A ───

def run_upstream_a(srt: Path, out: Path) -> None:
    subprocess.run([sys.executable, REPO / "SRT/qaqc_srt.py", srt, "-o", out], check=True, capture_output=True)


def run_candidate_a(srt: Path, out: Path) -> None:
    subprocess.run([sys.executable, REPO / "pipeline/candidates/phase_a_clean.py", srt, out], check=True, capture_output=True)


def phase_a(study: Path) -> dict:
    res = {}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for s in ZH_SESSIONS:
            sd = study / "sessions" / s
            truth = grams(core((sd / "cleaned.md").read_text(encoding="utf-8")))
            orig = parse_srt((sd / "transcript.srt").read_text(encoding="utf-8"))
            row = {"cues": len(orig)}
            for name, fn in (("upstream", run_upstream_a), ("candidate", run_candidate_a)):
                o = td / f"{s}.{name}.srt"
                fn(sd / "transcript.srt", o)
                kept = parse_srt(o.read_text(encoding="utf-8"))
                kept_tc = {b["timecode"] for b in kept}
                dropped = [b for b in orig if b["timecode"] not in kept_tc]
                false_drops = [b for b in dropped if overlap(b["text"], truth) >= 0.5]
                kept_low = [b for b in kept if overlap(b["text"], truth) < 0.2 and len(core(b["text"])) >= 6]
                row[name] = {"kept": len(kept), "dropped": len(dropped),
                             "han_kept": sum(len(CJK_RE.findall(b["text"])) for b in kept),
                             "latin_words_kept": sum(len(re.findall(r"[A-Za-z]{2,}", b["text"])) for b in kept),
                             "false_drops": len(false_drops),
                             "false_drop_examples": [b["text"][:60] for b in false_drops[:8]],
                             "kept_low_overlap": len(kept_low),
                             "kept_low_examples": [b["text"][:60] for b in kept_low[:5]]}
            u = {b["timecode"] for b in parse_srt((td / f"{s}.upstream.srt").read_text(encoding="utf-8"))}
            c = {b["timecode"] for b in parse_srt((td / f"{s}.candidate.srt").read_text(encoding="utf-8"))}
            by_tc = {b["timecode"]: b["text"] for b in orig}
            row["only_candidate_keeps"] = [by_tc[t][:60] for t in sorted(c - u)][:15]
            row["only_upstream_keeps"] = [by_tc[t][:60] for t in sorted(u - c)][:15]
            res[s] = row
            print(f"[phase-a] {s}: upstream false drops {row['upstream']['false_drops']}, "
                  f"candidate {row['candidate']['false_drops']}; differ +{len(c - u)}/-{len(u - c)}")
        # English: study's real EN path = srt_zhtw prep filter (+ drops.json), not qaqc_srt
        sd = study / "sessions" / EN_SESSION
        orig = parse_srt((sd / "transcript.srt").read_text(encoding="utf-8"))
        segs = json.loads((sd / "zhtw_work/segments.json").read_text(encoding="utf-8"))
        up_kept = {s["tc"] for s in segs}
        drops_ids = set(json.loads((sd / "zhtw_work/drops.json").read_text())) if (sd / "zhtw_work/drops.json").exists() else set()
        up_final = {s["tc"] for s in segs if s["i"] not in drops_ids}
        o = td / "en.candidate.srt"
        run_candidate_a(sd / "transcript.srt", o)
        ca = {b["timecode"] for b in parse_srt(o.read_text(encoding="utf-8"))}
        by_tc = {b["timecode"]: b["text"] for b in orig}
        res[EN_SESSION] = {"cues": len(orig), "upstream_prep_kept": len(up_kept), "upstream_after_semantic_drops": len(up_final),
                           "candidate_kept": len(ca),
                           "candidate_keeps_upstream_dropped": [by_tc[t][:70] for t in sorted(ca - up_kept)][:15],
                           "candidate_drops_upstream_kept": [by_tc[t][:70] for t in sorted(up_kept - ca)][:15],
                           "semantic_drops_candidate_still_keeps": len((up_kept - up_final) & ca)}
        print(f"[phase-a] {EN_SESSION}: upstream kept {len(up_kept)}, candidate kept {len(ca)}")
    save("phase_a", res)
    return res


# ─── Transcription ───

def load_study_keys(study: Path) -> dict:
    env = {}
    for line in (study / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("GROQ_API_KEY") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def transcribe(study: Path, start: int, secs: int) -> dict:
    res = {}
    keys = load_study_keys(study)
    if not keys:
        sys.exit("no GROQ_API_KEY in study/.env")
    scratch = Path(tempfile.mkdtemp(prefix="gsn-cmp-"))
    for s, lang in ((ZH_SESSIONS[3], "zh"), (EN_SESSION, "en")):
        sd = study / "sessions" / s
        src = next(sd.glob("source.*"))
        d = scratch / s
        d.mkdir()
        clip = d / "clip.m4a"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(secs), "-i", str(src.resolve()),
                        "-vn", "-ac", "1", "-ar", "16000", str(clip)], check=True)
        (d / ".env").symlink_to(study / ".env")             # upstream reads .env upward from the media dir
        ctx = d / "context.txt"
        shutil.copyfile(sd / "context.txt", ctx)
        up = REPO / (".claude/skills/good-student-notes/scripts/groq_transcribe.py" if lang == "zh"
                     else "scripts/lang/en/groq_transcribe_en.py")
        r1 = subprocess.run([sys.executable, up, clip, d / "up", ctx], capture_output=True, text=True)
        r2 = subprocess.run([sys.executable, REPO / "pipeline/candidates/transcribe_groq.py", clip, d / "cand.srt",
                             "--context", ctx], capture_output=True, text=True, env={**os.environ, **keys})
        up_srt = d / "up" / "clip.srt"
        row = {"clip": f"{start}s+{secs}s", "lang": lang, "upstream_exit": r1.returncode, "candidate_exit": r2.returncode,
               "candidate_note": r2.stdout.strip().splitlines()[-1:] if r2.stdout else r2.stderr[-200:]}
        texts = {}
        for name, p in (("upstream", up_srt), ("candidate", d / "cand.srt")):
            if not p.exists():
                row[name] = {"error": "no output"}
                continue
            cues = parse_srt(p.read_text(encoding="utf-8"))
            txt = "\n".join(b["text"] for b in cues)
            texts[name] = txt
            m = {"cues": len(cues), "han": len(CJK_RE.findall(txt)), "latin_words": len(re.findall(r"[A-Za-z]{2,}", txt)),
                 "prompt_echo_cues": sum(1 for b in cues if b["text"].startswith(("內容包含", "Key terms", "專有名詞", "Terms:")))}
            if lang == "zh":
                truth = grams(core((sd / "cleaned.md").read_text(encoding="utf-8")))
                m["precision_vs_published_text"] = round(overlap(txt, truth), 3)
                try:
                    from opencc import OpenCC
                    t2s, s2t = OpenCC("t2s"), OpenCC("s2t")
                    m["simplified_chars"] = sum(1 for c in txt if CJK_RE.match(c) and t2s.convert(c) == c and s2t.convert(c) != c
                                                and c not in "群裡台峰冰游干斗只伙")
                except ImportError:
                    pass
            row[name] = m
            samples = Path(tempfile.gettempdir()) / "gsn-compare-samples"     # third-party speech: never into the repo
            samples.mkdir(exist_ok=True)
            (samples / f"{s}.{name}.txt").write_text(txt[:1500], encoding="utf-8")
        if len(texts) == 2:
            a, b = grams(core(texts["upstream"])), grams(core(texts["candidate"]))
            row["agreement_4gram_jaccard"] = round(len(a & b) / max(1, len(a | b)), 3)
        res[s] = row
        print(f"[transcribe] {s}: {json.dumps({k: row.get(k) for k in ('upstream', 'candidate')}, ensure_ascii=False)[:300]}")
    shutil.rmtree(scratch, ignore_errors=True)       # the audio clip never stays anywhere
    save("transcribe", res)
    return res


# ─── Translation ───

def translate(study: Path) -> dict:
    sd = study / "sessions" / EN_SESSION
    wd_up = sd / "zhtw_work"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        up_wd = td / "up"
        shutil.copytree(wd_up, up_wd)
        r1 = subprocess.run([sys.executable, REPO / "scripts/lang/en/srt_zhtw.py", "assemble", up_wd, td / "up.srt",
                             "--orig", sd / "transcript.srt"], capture_output=True, text=True)
        rc1 = subprocess.run([sys.executable, REPO / "scripts/lang/en/zh_parts_check.py", up_wd], capture_output=True, text=True)
        # candidate: same source, same translations (mapped by timecode), its own prep/check/assemble
        cwd = td / "cand"
        subprocess.run([sys.executable, REPO / "pipeline/candidates/translate_srt.py", "prep", sd / "transcript.srt", cwd],
                       check=True, capture_output=True)
        segs_up = json.loads((wd_up / "segments.json").read_text(encoding="utf-8"))
        zh = {}
        for p in sorted((wd_up / "zh_parts").glob("*.json")):
            zh.update({int(k): v for k, v in json.loads(p.read_text(encoding="utf-8")).items()})
        drops = set(json.loads((wd_up / "drops.json").read_text())) if (wd_up / "drops.json").exists() else set()
        by_tc = {s["tc"]: zh[s["i"]] for s in segs_up if s["i"] in zh}
        segs_c = json.loads((cwd / "segments.json").read_text(encoding="utf-8"))
        part, cdrops = {}, []
        for s in segs_c:
            if s["tc"] in by_tc:
                part[str(s["i"])] = by_tc[s["tc"]]
            else:
                cdrops.append(s["i"])                      # cues upstream prep or drops.json removed
        (cwd / "parts" / "part_all.json").write_text(json.dumps(part, ensure_ascii=False), encoding="utf-8")
        (cwd / "drops.json").write_text(json.dumps(cdrops))
        r2 = subprocess.run([sys.executable, REPO / "pipeline/candidates/translate_srt.py", "check", cwd], capture_output=True, text=True)
        r3 = subprocess.run([sys.executable, REPO / "pipeline/candidates/translate_srt.py", "assemble", cwd, td / "cand",
                             "--orig", sd / "transcript.srt"], capture_output=True, text=True)
        up_cues = parse_srt((td / "up.srt").read_text(encoding="utf-8")) if (td / "up.srt").exists() else []
        c_cues = parse_srt((td / "cand" / "translated.zh-TW.srt").read_text(encoding="utf-8")) if (td / "cand/translated.zh-TW.srt").exists() else []
        res = {"upstream": {"assemble_exit": r1.returncode, "assemble": r1.stdout.strip().splitlines()[-2:],
                            "check_exit": rc1.returncode, "check": rc1.stdout.strip().splitlines()[-3:], "cues": len(up_cues),
                            "prep_drops_automatic": True, "outputs": ["translated SRT"]},
               "candidate": {"assemble_exit": r3.returncode, "assemble": r3.stdout.strip().splitlines()[-1:] or r3.stderr[-300:],
                             "check_exit": r2.returncode, "check": r2.stdout.strip().splitlines()[-3:], "cues": len(c_cues),
                             "prep_drops_automatic": False, "outputs": ["translated SRT", "bilingual SRT"]},
               "identical_output": [(a["timecode"], a["text"]) for a in up_cues] == [(b["timecode"], b["text"]) for b in c_cues],
               "upstream_drops_json": len(drops)}
    save("translate", res)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:1500])
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["phase-a", "transcribe", "translate"])
    ap.add_argument("--study", default=str(Path.home() / "Desktop/study"))
    ap.add_argument("--clip-start", type=int, default=600)
    ap.add_argument("--clip-seconds", type=int, default=300)
    a = ap.parse_args()
    study = Path(a.study).expanduser()
    {"phase-a": lambda: phase_a(study), "transcribe": lambda: transcribe(study, a.clip_start, a.clip_seconds),
     "translate": lambda: translate(study)}[a.what]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
