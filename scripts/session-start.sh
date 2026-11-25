#!/usr/bin/env bash
set -eo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$HERE/bin/oat-postcard"

payload="$(cat)"
session_id="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id",""))')"
cwd="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd",""))')"

args=(--quiet --pid "$PPID")
[[ -n "$session_id" ]] && args+=(--session-id "$session_id")
[[ -n "$cwd" ]] && args+=(--cwd "$cwd")

"$CLI" session-init "${args[@]}" >/dev/null 2>&1 || true
