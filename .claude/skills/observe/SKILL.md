---
name: observe
description: Write the QAQC observation report for a finished session — reads the ledger, audit and agent logs and flags shortcuts (skipped or bundled stages, hand edits, summarising, gate gaming). Run in a fresh context, ideally on Sonnet.
disable-model-invocation: true
---

`<repo>` = the repository root; run every command from there.


Run `python3 gsn.py audit $ARGUMENTS`, then follow `<repo>/prompts/observer.md` exactly for session `$ARGUMENTS`
and write `<repo>/sessions/$ARGUMENTS/observer_report.md`. You are the observer: do not fix anything.
If this conversation already did work on the session, say so in the report — the observer should be a
fresh context (e.g. `claude -p "/observe <slug>" --model sonnet`).
