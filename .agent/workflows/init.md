---
description: Set up this repository after cloning — check Python, ffmpeg, the Groq key in .env, the secret-scan git hook and the Phase 6 extras, fixing what can be fixed. Replaces the built-in /init here; this repo already has its CLAUDE.md.
---

`<repo>` = the repository root; run every command from there.


# /init — first-run setup for Good-Student Notes

This repository already has its constitution (`CLAUDE.md`). Do NOT generate or rewrite CLAUDE.md.

1. Run `python3 gsn.py doctor --fix <args>` from the repo root and show the user the table.
2. For each remaining FAIL line, give the exact fix in Traditional Chinese (the user is a human reader):
   - `GROQ_API_KEY set in .env` → walk them through README §1 (console.groq.com → API Keys → Create API Key →
     paste into `.env` as `GROQ_API_KEY=gsk_…`). Never ask them to paste the key into the chat; never print it.
   - `ffmpeg` → the install command for their OS.
   - `repo folder writable` (macOS) → System Settings → Privacy & Security → Files and Folders / Full Disk Access.
3. When everything required is OK, run `python3 gsn.py doctor --check-key` once to prove the key works,
   then suggest the first run on the bundled example (no Groq call):
   `python3 gsn.py new --from-srt <repo>/examples/talk-context/excerpt.srt --context <repo>/examples/talk-context/context.txt`
4. Finish with one line telling them how to process their own recording (README §3).
