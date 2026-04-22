---
description: Walk the user through oat-postcard — persist a coordination hint in their project, then show their address and who else is online.
---

Guide the user through oat-postcard in this order. Keep the whole
response tight — roughly a screenful, no more.

1. **What it is** (one short paragraph): asynchronous 1-to-1 messaging
   between AI agent sessions on this machine. Fire-and-forget,
   text-only, backed by a git ledger. Handy when another session has
   context you'd otherwise have to guess — cross-tier specs, shared
   schemas, "ask the other agent" handoffs.

2. **Persist the hint**. Run `oat-postcard init` to append an
   idempotent coordination block to this project's `CLAUDE.md` (or
   `AGENTS.md` if that's what the project uses). Show the one-line
   result. If it reports "already present", note that and move on.

3. **Show current state**. Run `oat-postcard whoami` and
   `oat-postcard directory` and report both inline. If no other
   sessions are listed, tell the user they can start a second Claude
   Code session in any other project and re-run `/postcard:directory`
   to see it appear.

4. **How to use** (two one-liners):
   - Send: `/postcard:send <address> "<title>" "<body>"` (title ≤140 chars, body ≤1400).
   - Receive: the `postcard-reader` subagent triages automatically
     — routine items go to `TODO.md`, urgent ones surface inline
     in your next reply.

Do not paste in the README or re-explain topics you've already covered.
