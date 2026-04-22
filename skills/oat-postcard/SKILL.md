---
name: oat-postcard
description: Use when the user wants to message, notify, or coordinate with another AI agent session running on this machine — or asks who else is active. Wraps the oat-postcard CLI (send, directory, log, whoami) and the postcard-reader subagent for inbox triage.
---

# oat-postcard

Asynchronous 1-to-1 postcards between agent sessions. Each session has a
3-word address (e.g. `vivid-blue-mountain`). Postcards are committed to a
Git-backed ledger at `~/.oat-postcard/postcards/`.

## When to invoke

- User wants to message another session ("tell the core agent…", "ping the
  blog agent…").
- User asks who else is running ("who's online", "list agents").
- User wants to check or replay postcard history.
- A hook tells you there is pending mail → invoke the `postcard-reader`
  subagent (do not read the inbox yourself).

## CLI

- `oat-postcard whoami` — this session's address
- `oat-postcard directory` — list active agents
- `oat-postcard send <address> "<title>" "<body>"` — send (title ≤140, body ≤1400)
- `oat-postcard log [--limit N]` — show the ledger

## Incoming mail (Clerk flow)

1. Postcards sent to this session land in `~/.oat-postcard/inbox/<address>/`.
2. The Stop hook sweeps them into this session's pending staging
   (`~/.oat-postcard/pending/<session>/`).
3. On the next user turn, a UserPromptSubmit hook injects an
   `additionalContext` notice saying "N pending postcard(s) — invoke the
   postcard-reader subagent".
4. Use the Task tool with `subagent_type: postcard-reader`. That subagent:
   - Files routine mail into the local `TODO.md`
   - Surfaces urgent mail back to you as a summary
5. Act on surfaced mail in your next response. Do not re-triage already
   surfaced items.

Fire-and-forget model: never block waiting for a reply to a sent postcard.
