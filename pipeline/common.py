"""common.py — shared helpers for every pipeline tool.

Paths, SRT parse/format, character metrics, the session ledger (hash-chained, append-only)
and marker files. Every tool imports from here so that "how we count" and "how we log"
have exactly one definition.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SESSIONS = REPO / "sessions"
PROMPTS = REPO / "prompts"

# ─── Stage graph (single source of truth for order, artifacts and prompts) ───
# kind: "tool" = deterministic, run by gsn.py itself; "judgment" = handed to an agent via a marker.
STAGES = [
    {"id": "p1-transcribe", "phase": 1, "kind": "tool",     "title": "Groq Whisper → transcript.srt (immutable)"},
    {"id": "p1-clean",      "phase": 1, "kind": "tool",     "title": "Phase A deterministic clean → cleaned.srt"},
    {"id": "p2-translate",  "phase": 2, "kind": "judgment", "title": "Timeline-locked translation → bilingual SRT",
     "prompt": "prompts/phase2_translate.md", "optional": True},
    {"id": "p3-polish",     "phase": 3, "kind": "judgment", "title": "Phase B polish: punctuation, paragraphs, headings → cleaned.md",
     "prompt": "prompts/phase3_polish.md"},
    {"id": "p3-punct",      "phase": 3, "kind": "judgment", "title": "Phase C punctuation: full-width tool + colon judgment",
     "prompt": "prompts/phase3_punct.md"},
    {"id": "p3-hooks",      "phase": 3, "kind": "judgment", "title": "Phase D hooks: insert-only connective phrases",
     "prompt": "prompts/phase3_hooks.md"},
    {"id": "p4-terms",      "phase": 4, "kind": "judgment", "title": "Term supplements → enhanced.md",
     "prompt": "prompts/phase4_terms.md", "optional": True},
    {"id": "p5-stance",     "phase": 5, "kind": "judgment", "title": "Stance notes → notes_<identity>.md",
     "prompt": "prompts/phase5_stance.md", "optional": True},
    {"id": "p6-matrix",     "phase": 6, "kind": "judgment", "title": "Good-Student Matrix (I / II / III / IV)",
     "prompt": "prompts/phase6_matrix.md", "optional": True},
]
STAGE_BY_ID = {s["id"]: s for s in STAGES}
STAGE_ORDER = [s["id"] for s in STAGES]
STOP_AT = ["p1", "p2", "p3", "p4", "p5", "p6"]


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha1_file(p: Path) -> str | None:
    return hashlib.sha1(p.read_bytes()).hexdigest() if p.is_file() else None


def session_dir(slug_or_path: str) -> Path:
    p = Path(slug_or_path)
    if p.is_dir():
        return p.resolve()
    return SESSIONS / slug_or_path


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


# ─── SRT ───

def parse_srt(content: str) -> list[dict]:
    """[{'timecode': '00:00:00,000 --> 00:00:05,500', 'text': '...'}]; tolerates a missing index line."""
    out = []
    for block in content.strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) >= 3 and "-->" in lines[1]:
            out.append({"timecode": lines[1].strip(), "text": "\n".join(lines[2:]).strip()})
        elif len(lines) >= 2 and "-->" in lines[0]:
            out.append({"timecode": lines[0].strip(), "text": "\n".join(lines[1:]).strip()})
    return out


def format_srt(blocks: list[dict]) -> str:
    return "\n".join(f"{i}\n{b['timecode']}\n{b['text']}\n" for i, b in enumerate(blocks, 1))


def srt_text(srt_path: Path) -> str:
    """SRT text only (no index, no timecode), one cue per line."""
    return "\n".join(b["text"] for b in parse_srt(srt_path.read_text(encoding="utf-8")))


# ─── Metrics (one counting rule everywhere — CLAUDE.md "same-basis comparison") ───

CJK_RE = re.compile(r"[一-鿿㐀-䶿]")
IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:['’][A-Za-z]+)?")


def is_cjk_text(text: str) -> bool:
    """Treat a text as CJK when Han characters are at least 30% of its letters."""
    han = len(CJK_RE.findall(text))
    words = len(WORD_RE.findall(text))
    return han >= 0.3 * max(1, han + words)


def content_units(text: str, cjk: bool | None = None) -> int:
    """Han characters for CJK text, words otherwise. Images and markup are excluded."""
    text = IMG_RE.sub("", text)
    if cjk is None:
        cjk = is_cjk_text(text)
    return len(CJK_RE.findall(text)) if cjk else len(WORD_RE.findall(text))


# ─── Ledger: append-only, hash-chained (tamper-evident) ───

def ledger_path(sdir: Path) -> Path:
    return sdir / "ledger.jsonl"


def read_ledger(sdir: Path) -> list[dict]:
    p = ledger_path(sdir)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def append_ledger(sdir: Path, action: str, stage: str | None = None, **fields) -> dict:
    entries = read_ledger(sdir)
    entry = {"seq": len(entries) + 1, "ts": now(), "action": action, "stage": stage,
             "actor": fields.pop("actor", os.environ.get("GSN_ACTOR", "unknown")),
             **fields, "prev": entries[-1]["hash"] if entries else None}
    entry["hash"] = _entry_hash(entry)
    with ledger_path(sdir).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify_chain(entries: list[dict]) -> list[str]:
    errs, prev = [], None
    for i, e in enumerate(entries, 1):
        if e.get("seq") != i:
            errs.append(f"seq {e.get('seq')} at line {i}")
        if e.get("prev") != prev:
            errs.append(f"seq {i}: prev-hash mismatch (entry inserted, removed or reordered)")
        if _entry_hash(e) != e.get("hash"):
            errs.append(f"seq {i}: content hash mismatch (entry edited by hand)")
        prev = e.get("hash")
    return errs


# ─── Markers ───

def marker_path(sdir: Path, stage: str) -> Path:
    return sdir / f".{stage}.pending.json"


def pending_markers(sdir: Path) -> list[str]:
    found = {p.name[1:-len(".pending.json")] for p in sdir.glob(".*.pending.json")}
    return [s for s in STAGE_ORDER if s in found]


def load_meta(sdir: Path) -> dict:
    p = sdir / "metadata.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_meta(sdir: Path, meta: dict) -> None:
    (sdir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
