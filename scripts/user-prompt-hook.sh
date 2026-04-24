#!/usr/bin/env bash
# UserPromptSubmit hook: if this session has pending postcards, inject
# additionalContext so the main agent invokes the postcard-reader subagent.
#
# Also lazily registers the session if SessionStart never fired.
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

count="$("$CLI" clerk-pending --count 2>/dev/null || echo 0)"
count="${count//[^0-9]/}"
count="${count:-0}"

if [[ "$count" -gt 0 ]]; then
  python3 - "$count" <<'PY'
import json, sys
n = sys.argv[1]
msg = (
    f"postcard: {n} pending postcard(s) from other agent sessions. "
    "Before answering, invoke the postcard-reader subagent via the Task tool "
    "(subagent_type='postcard:postcard-reader') to triage them. The subagent will file "
    "routine mail into TODO.md and surface urgent mail back for your response."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg,
    }
}))
PY
fi
