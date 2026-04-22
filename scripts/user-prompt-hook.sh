#!/usr/bin/env bash
# UserPromptSubmit hook: if this session has pending postcards, inject
# additionalContext so the main agent invokes the postcard-reader subagent.
set -eo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$HERE/bin/oat-postcard"

payload="$(cat 2>/dev/null || true)"
if [[ -n "${payload:-}" ]]; then
  session_id="$(printf '%s' "$payload" | python3 -c '
import json, sys
try: print(json.load(sys.stdin).get("session_id", ""))
except Exception: pass
' 2>/dev/null || true)"
  [[ -n "${session_id:-}" ]] && export CLAUDE_SESSION_ID="$session_id"
fi

count="$("$CLI" clerk-pending --count 2>/dev/null || echo 0)"
count="${count//[^0-9]/}"
count="${count:-0}"

if [[ "$count" -gt 0 ]]; then
  python3 - "$count" <<'PY'
import json, sys
n = sys.argv[1]
msg = (
    f"oat-postcard: {n} pending postcard(s) from other agent sessions. "
    "Before answering, invoke the postcard-reader subagent via the Task tool "
    "(subagent_type='postcard-reader') to triage them. The subagent will file "
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
