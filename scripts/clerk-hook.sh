#!/usr/bin/env bash
set -eo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$HERE/bin/oat-postcard"

payload="$(cat 2>/dev/null || true)"
session_id=""
cwd=""
if [[ -n "${payload:-}" ]]; then
  session_id="$(printf '%s' "$payload" | python3 -c '
import json, sys
try: print(json.load(sys.stdin).get("session_id", ""))
except Exception: pass
' 2>/dev/null || true)"
  cwd="$(printf '%s' "$payload" | python3 -c '
import json, sys
try: print(json.load(sys.stdin).get("cwd", ""))
except Exception: pass
' 2>/dev/null || true)"
  [[ -n "${session_id:-}" ]] && export CLAUDE_SESSION_ID="$session_id"
fi

init_args=(--quiet --pid "$PPID")
[[ -n "${session_id:-}" ]] && init_args+=(--session-id "$session_id")
[[ -n "${cwd:-}" ]] && init_args+=(--cwd "$cwd")
"$CLI" session-init "${init_args[@]}" >/dev/null 2>&1 || true

"$CLI" clerk-sweep --quiet >/dev/null 2>&1 || true
