#!/usr/bin/env bash
# Stop hook (post-turn): let the Clerk sweep this session's inbox.
set -euo pipefail

payload="$(cat 2>/dev/null || true)"
session_id=""
cwd=""
if [[ -n "$payload" ]]; then
  session_id="$(printf '%s' "$payload" | python3 -c 'import json,sys;
try: print(json.load(sys.stdin).get("session_id",""))
except Exception: pass' 2>/dev/null || true)"
  cwd="$(printf '%s' "$payload" | python3 -c 'import json,sys;
try: print(json.load(sys.stdin).get("cwd",""))
except Exception: pass' 2>/dev/null || true)"
fi

export CLAUDE_SESSION_ID="${session_id:-${CLAUDE_SESSION_ID:-}}"
todo_arg=()
if [[ -n "$cwd" && -d "$cwd" ]]; then
  todo_arg=(--todo "$cwd/TODO.md")
fi

PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" python3 -m oat_postcard clerk-check "${todo_arg[@]}" >/dev/null 2>&1 || true
