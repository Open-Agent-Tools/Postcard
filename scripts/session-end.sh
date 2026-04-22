#!/usr/bin/env bash
# SessionEnd hook: remove this session from the global directory.
set -eo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$HERE/bin/oat-postcard"

payload="$(cat)"
session_id="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id",""))')"

args=()
[[ -n "$session_id" ]] && args+=(--session-id "$session_id")

"$CLI" session-end "${args[@]}" >/dev/null 2>&1 || true
