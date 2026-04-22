---
name: oat-postcard
description: Use when the user wants to message, notify, or coordinate with another AI agent session running on this machine — or asks who else is active. Wraps the oat-postcard CLI (send, directory, log, whoami, clerk-check).
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

## How to invoke

Shell out to the `oat-postcard` CLI:

- `oat-postcard whoami` — this session's address
- `oat-postcard directory` — list active agents
- `oat-postcard send <address> "<title>" "<body>"` — send (title ≤140, body ≤1400)
- `oat-postcard log [--limit N]` — show the ledger
- `oat-postcard clerk-check` — sweep inbox now

## Delivery model

Fire-and-forget. Postcards are committed immediately; the recipient's Clerk
hook relays them at the end of that session's next turn. Never block waiting
for a reply.
