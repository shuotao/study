# Example run — 〈說話與聽話〉 through Phases 1–6

The bundled talk (`examples/talk-context/transcript.srt`) run end to end on 2026-10-22, unattended:
Fable 5.1 orchestrator (headless `claude -p`), one Opus 5.5 implementer per Phase 3–5 stage (effort low),
Sonnet 5.5 workers per matrix data file, four fresh Opus verifiers, then a fresh Sonnet observer.
Brief used: `../example-run-orchestrator-prompt.md`.

| File | What |
|---|---|
| `observer_report.md` | Sonnet observer, fresh context — verdict TRUSTWORTHY WITH NOTES |
| `orchestrator_log.md` | every decision Fable made in place of the human, rounds, findings |
| `audit_report.json` | `gsn.py audit` — 46/46 green |
| `wordcount_report.json` | word-count chain 6588 → 6748 → 6748 → 6795 (all bands pass) |
| `ledger.jsonl`, `metadata.json` | the session record |
| `products/` | `cleaned.md` (full text, II), `enhanced.md` (+ terms), `notes_工程師.md` (stance notes) |
| `matrix/` | K / I / III / IV data and the rendered pages (open `matrix/index.html`) |

Copies, not the live session (`sessions/` is never committed). Two absolute local paths in the ledger copy were
replaced by `<repo>/`, so this copy's hash chain no longer verifies; the audit (A0) ran on the original.
Obsidian links (local vault paths) were removed from `matrix/iv.html`. Since then gates pass repo-relative paths.
