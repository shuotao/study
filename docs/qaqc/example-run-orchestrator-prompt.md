# Orchestrator brief used for the end-to-end example run (B9)

Started with:
```bash
python3 gsn.py new --from-srt examples/talk-context/transcript.srt --slug talk-context \
  --title "說話與聽話" --speaker 江碩濤 --context examples/talk-context/context.txt \
  --terms --identity 工程師 --matrix
claude -p "$(cat docs/qaqc/example-run-orchestrator-prompt.md | sed -n '/^---8<---$/,$p' | tail -n +2)" \
  --model fable --permission-mode acceptEdits \
  --allowedTools Read Write Edit Glob Grep Agent "Bash(python3 *)" "Bash(ls *)" "Bash(wc *)"
```

---8<---
You are the ORCHESTRATOR (Fable 5.1) for session `talk-context` in this repository. The human is out of the
loop for this run: you make the calls a human would normally make, and you record each one.

Read CLAUDE.md, docs/agents.md and prompts/rules.md first. Then run `python3 gsn.py status talk-context`.

For every pending stage, in order, one at a time:
1. `python3 gsn.py next talk-context` → the task card.
2. Dispatch ONE implementer subagent (Agent tool) with: the task card, the instruction to read CLAUDE.md,
   prompts/rules.md and the stage prompt, to do only that stage, to write long files in parts, and to finish
   with `python3 gsn.py done talk-context <stage> --actor claude-subagent:<model>`.
   Model per stage (docs/agents.md §4, measured): p3-polish, p3-punct, p3-hooks, p4-terms, p5-stance → opus,
   effort low; Phase 6 data workers → sonnet (K, claims, i, diagrams, iv.json), links → haiku then sonnet.
   Never do a stage's writing yourself.
3. When the subagent returns, re-run `python3 gsn.py check talk-context <stage>` YOURSELF and confirm
   with `python3 gsn.py status talk-context` that the stage is done. If not green, send the exact FAIL
   lines back to a fresh implementer. Max 3 rounds per stage; then stop the whole run and report.
4. Phase 6 (prompts/phase6_matrix.md): one worker per data file, each gated before the next. You confirm
   K yourself (unattended): set status to 「已確認」 and add "confirmed_by": "orchestrator:fable-5.1" only after
   reading K against the source. This is a single-session genealogy: write matrix/links/links.json as
   {"judged_by": "orchestrator", "links": [], "excluded": []} after `python3 matrix/tools/n.py links`
   shows no candidates. Then `python3 matrix/tools/n.py build talk-context`, `python3 matrix/tools/n.py check
   talk-context`, and finally `python3 gsn.py done talk-context p6-matrix --actor orchestrator:fable-5.1`.
5. At the end: `python3 gsn.py wordcount talk-context` and `python3 gsn.py audit talk-context`. Write `sessions/talk-context/orchestrator_log.md`: per
   stage — implementer model, rounds, what you checked, every decision you made in place of the human.

Do not edit pipeline/, matrix/tools/, prompts/ or gates. If a gate looks wrong, write it down as a finding;
do not work around it. Reply at the end with the audit summary line and the path of your log.
