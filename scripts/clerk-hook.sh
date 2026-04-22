#!/usr/bin/env bash
# Stop hook (post-turn): sweep this session's inbox into pending staging.
# Silent on success; the UserPromptSubmit hook tells the main agent
# about pending mail on the next user turn.
set -euo pipefail

payload="$(cat 2>/dev/null || true)"
if [[ -n "$payload" ]]; then
  session_id="$(printf '%s' "$payload" | python3 -c '
import json, sys
try: print(json.load(sys.stdin).get("session_id", ""))
except Exception: pass
' 2>/dev/null || true)"
  [[ -n "$session_id" ]] && export CLAUDE_SESSION_ID="$session_id"
fi

oat-postcard clerk-sweep --quiet >/dev/null 2>&1 || true
