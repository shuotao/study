---
name: good-student-notes
description: Turn a talk recording (audio/video) or an SRT into a zero-omission transcript, readable full text, bilingual subtitles, term supplements, stance notes (好學生筆記) and the four-quadrant Good-Student Matrix (好學生矩陣). Use when the user gives a media file or SRT and asks for 逐字稿, 字幕, 筆記, 好學生筆記, 好學生矩陣, transcript or notes.
---

`<repo>` = the repository root; run every command from there.


# Good-Student Notes pipeline

You are the orchestrator for one session unless the user assigned you a narrower role. Read `CLAUDE.md` first.

1. **Context first.** Before transcribing, ask for (or confirm) the context: speaker names, company/product
   names, key terms. Names are the most error-prone part of ASR; they also seed `context.txt`.
2. **Start:** `python3 gsn.py new <media> --context "<context>" [options]` (or `--from-srt <file>`).
   Choose phases with the user: Phase 3 full text is the default end point; add `--translate`, `--terms`,
   `--identity`, `--matrix` only when asked.
3. **Loop, one stage at a time:** `python3 gsn.py next <slug>` → read the stage prompt in `prompts/` →
   do exactly that stage (or dispatch it to an implementer subagent / `gsn.py headless`) →
   `python3 gsn.py done <slug> <stage> --actor <cli>:<model>`. Gate red → fix → again (max 3 rounds,
   then stop and report). Never bundle stages; never delete markers or ledger lines.
4. **Phase 6** follows `<repo>/prompts/phase6_matrix.md` and `<repo>/matrix/SPEC.md` (one worker per data file).
5. **Close:** `python3 gsn.py audit <slug>` must be all green; then dispatch the observer (`/observe <slug>`).
   Report what was produced, where, the audit result and the observer verdict — failures as failures.

Long texts: write files in parts, never one huge output; the zero-omission rule is unchanged.
