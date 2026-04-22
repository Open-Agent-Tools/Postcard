---
description: Reply to a postcard. Recipient and title auto-derived from the parent.
argument-hint: <parent-id> "<body>"
---

Run: `oat-postcard reply $ARGUMENTS`

Recipient is the parent postcard's sender. Title is
`"Re: <parent-title>"` (truncated to 140 chars). The new postcard
records `reply_to: <parent-id>` so threading is queryable and the
receiving session can see this is a direct response to something
they sent.

Body ≤1400 chars, plain text only.
