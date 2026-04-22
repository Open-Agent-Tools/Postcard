---
description: List recent postcards addressed to this session (passive — no triage).
argument-hint: "[--limit N] [--watch]"
---

Run: `oat-postcard inbox $ARGUMENTS`

Shows the last N postcards addressed to this session (default 20), one
line per entry. Pass `--watch` to tail mode (prints new arrivals as
they land; exits on Ctrl-C). A ↳-prefixed id on a line means the
postcard is a reply to that earlier postcard.

Incoming mail is triaged automatically on every turn by the
`postcard-reader` subagent — this command is for passive observation,
not to trigger triage.
