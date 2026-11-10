#!/usr/bin/env bash
# Single entry point for every host's lifecycle hooks.
#
#   hook.sh <session-start|session-end|stop|prompt> [--host <name>|auto]
#
# The host CLI pipes its JSON payload on stdin. The Python side normalizes
# it (session_id / sessionId / conversationId, cwd / workspacePaths, ...),
# performs the action, and prints whatever JSON that host expects back.
#
# $PPID here is the host CLI's long-lived process (the parent of this
# script's shell), which is the PID recorded for liveness in the directory.
#
# Hooks are fail-open: this script never exits non-zero.
set -eo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$HERE/bin/oat-postcard"

"$CLI" hook "$@" --pid "$PPID" || true
