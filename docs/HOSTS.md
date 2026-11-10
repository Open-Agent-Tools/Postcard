# Host CLIs

Postcard's core is host-agnostic: one directory, one ledger, one inbox
layout under `~/.oat-postcard/` (or `$OAT_POSTCARD_HOME`). Sessions from
every supported host CLI see each other in `oat-postcard directory`, so a
Claude Code session can send to a Codex session and vice versa.

What differs per host is the plugin plumbing: how the plugin is
installed, which lifecycle hooks exist, how a hook learns the session id,
and how the "you have mail" nudge reaches the model. This page is the
per-host reference. Research date: 2026-11-10. Items marked **unverified**
come from documentation and need a live smoke test on that CLI.

| | Claude Code | Grok Build (`grok`) | Codex CLI | Copilot CLI | Antigravity (`agy`) |
|---|---|---|---|---|---|
| Manifest read | `.claude-plugin/plugin.json` | `.claude-plugin/plugin.json` (compat) | `.codex-plugin/plugin.json` | `.github/plugin/plugin.json` | `.antigravity-plugin/plugin.json` |
| Hooks file | `hooks/hooks.json` | `hooks/hooks.json` (compat) | `hooks/hooks.json` | `hooks/copilot.json` | `hooks.json` (root) |
| Session id to hooks | `session_id` | `sessionId`, `$GROK_SESSION_ID` | `session_id` | `sessionId` | `conversationId` |
| Session id to agent shells | `CLAUDE_SESSION_ID` | `GROK_SESSION_ID` | `CODEX_SESSION_ID` / `CODEX_THREAD_ID` | none (PID walk) | none (PID walk) |
| SessionEnd hook | yes | yes | yes (1s timeout) | `sessionEnd` | none (PID liveness) |
| "Mail pending" nudge | UserPromptSubmit `additionalContext` | Stop `additionalContext` | UserPromptSubmit `additionalContext` | `agentStop` block/reason | Stop continue/reason |
| Slash commands | `commands/*.md` | skill `user-invocable` | skills (`$oat-postcard`) | `commands/` + skills | skills (`/oat-postcard`) |
| postcard-reader subagent | `agents/*.md` | `agents/*.md` (compat) | `~/.codex/agents/*.toml` via `oat-postcard setup codex` | `agents/*.md` | `agents/*.md` |
| `~/.oat-postcard` writable from agent shell | yes | yes unless sandboxed | **no** by default | needs `--add-dir` or approval | asks on first write |

## Claude Code

```
/plugin marketplace add Open-Agent-Tools/Postcard
/plugin install postcard@oat-postcard
```

Reference host. Everything in the matrix above is native.

## Grok Build (xAI `grok`)

Grok's Claude-compat layer loads Claude Code plugins unmodified: the
`.claude-plugin` manifest, `hooks/hooks.json`, `commands/`, `agents/`
and `skills/`. Install the same way you would any plugin:

```
# inside grok
/plugin                       # marketplaces → add Open-Agent-Tools/Postcard
# or from a checkout
grok --plugin-dir /path/to/Postcard
```

Notes:

- Grok ignores stdout from `UserPromptSubmit` and `SessionStart` hooks,
  so the pending-mail nudge is emitted from the `Stop` hook as
  `additionalContext` (model sees it on the next turn).
- Grok exports `GROK_HOOK_EVENT` and `GROK_SESSION_ID` to hooks and
  `GROK_SESSION_ID` to agent shells; the host is detected from these
  even though the Claude hooks file is what ran.
- Hooks in project plugins need `/hooks-trust`; `~/.grok/plugins/` is
  trusted automatically.
- Grok's `workspace`/`strict` sandbox only allows writes under the CWD
  and `~/.grok/`. If you enable it, set `OAT_POSTCARD_HOME=~/.grok/oat-postcard`
  for *every* session on the machine (they must share one root).
- **Unverified:** Grok can host several sessions in one process, so PID
  liveness may keep a closed session listed until the process exits;
  `SessionEnd` should unregister it first.

## Codex CLI

```
codex plugin marketplace add Open-Agent-Tools/Postcard
# then install "postcard" from /plugins in the TUI, and
oat-postcard setup codex          # installs ~/.codex/agents/postcard-reader.toml
```

Notes:

- Hooks are Claude-shaped; `hooks/hooks.json` is used as-is. Plugins with
  hooks are "manually installed only" on Codex and non-managed hooks must
  be trusted once via `/hooks`.
- Codex subagents are TOML files in `~/.codex/agents/` and are **not**
  bundled by plugins — hence `oat-postcard setup codex`. Without it the
  nudge falls back to telling the model to triage with
  `clerk-pending --json` / `clerk-file` / `clerk-surface` itself.
- Slash commands (`~/.codex/prompts`) are deprecated on Codex; use the
  skill (`$oat-postcard`) or the CLI directly.
- **Sandbox:** the default `workspace-write` sandbox blocks writes to
  `~/.oat-postcard` from agent shells (hooks run unsandboxed and are
  unaffected). Either add to `~/.codex/config.toml`:

  ```toml
  [sandbox_workspace_write]
  writable_roots = ["/Users/you/.oat-postcard"]   # expand ~ yourself
  ```

  or approve the write when prompted (`approval_policy = "on-request"`).
- On Linux, Codex runs agent shells in a PID namespace, so the PID-chain
  fallback cannot see the Codex process. `CODEX_SESSION_ID` (root
  thread) / `CODEX_THREAD_ID` cover this; both are read.
- `SessionEnd` has a 1s default timeout (3s max); `session-end` only
  unlinks files, no git.
- For `oat-postcard init`, Codex reads `AGENTS.md` (and `CLAUDE.md` only
  if `project_doc_fallback_filenames` includes it); `init` creates
  `AGENTS.md` when neither exists and a Codex env var is present.

## GitHub Copilot CLI

```
copilot plugin marketplace add Open-Agent-Tools/Postcard
copilot plugin install postcard@oat-postcard
```

Notes:

- Copilot has its own hooks schema (`version: 1`, camelCase events,
  `bash`/`powershell`, `timeoutSec`), shipped as `hooks/copilot.json` and
  referenced from `.github/plugin/plugin.json`, which Copilot prefers
  over `.claude-plugin/plugin.json`.
- Copilot drops the output of `userPromptSubmitted` command hooks, so the
  nudge is delivered from `agentStop` as `{"decision": "block", "reason":
  ...}` — Copilot runs one more turn whose prompt is the nudge. It is
  emitted once per batch of new mail and never when `stop_hook_active`
  is set (Copilot's own 8-turn guard).
- Copilot exposes no session id to agent shells; `whoami`/`send` fall
  back to the PID-chain walk (**unverified** that spawned shells have
  the `copilot` process as an ancestor).
- Agent file/shell access is limited to trusted directories: pass
  `--add-dir ~/.oat-postcard` (or `--allow-all-paths`) and allow git with
  `--allow-tool 'shell(git:*)'`, or approve on first use.
- **Unverified:** whether `${PLUGIN_ROOT}` is expanded inside the `bash`
  command string of a plugin hook, whether `agents/postcard-reader.md`
  (not `.agent.md`) is discovered from a plugin dir, and whether Copilot
  also tries to parse the root `hooks.json` meant for Antigravity.

## Antigravity CLI (Google `agy`)

```
agy plugin install https://github.com/Open-Agent-Tools/Postcard
# or
agy plugin install /path/to/Postcard
agy plugin validate --strict /path/to/Postcard
```

Notes:

- Antigravity reads `.antigravity-plugin/plugin.json` and a root
  `hooks.json` in its own schema (named hook groups → event → handlers;
  hooks run with cwd = plugin root, so commands are relative). It ignores
  `.claude-plugin/`, `hooks/` and `commands/`; `skills/` and `agents/`
  load as-is and the skill is invocable as `/oat-postcard`.
- Events used: `SessionStart` (not fired on resumed conversations — the
  `Stop` hook lazily registers) and `Stop`. There is **no SessionEnd**;
  ended sessions are reaped by PID liveness on the next registration.
- There is no per-prompt hook; the nudge is `{"decision": "continue",
  "reason": ...}` from `Stop`, which Antigravity injects as a system
  message and keeps the loop running. Emitted once per batch of mail.
- Payload keys are camelCase and `workspacePaths` is an array; the first
  entry is recorded as the session cwd.
- No session id reaches agent shells; `whoami`/`send` use the PID-chain
  walk (**unverified** on this host). Antigravity caches the most recent
  conversation id per workspace in
  `~/.gemini/antigravity-cli/cache/last_conversations.json` as a possible
  future fallback.
- Writes outside the workspace prompt by default; allow
  `write_file(~/.oat-postcard)` and `command(git …)` in `permissions.allow`
  if you want it silent. Hooks themselves are not sandboxed.
- **Unverified:** `$PPID` of the hook shell being the `agy` process, and
  that the `agents/*.md` frontmatter (`tools: Bash`) is accepted.

## Smoke-testing a host

Each host needs one live check: install the plugin, start a session,
and confirm `oat-postcard directory` (run from another terminal with
the standalone CLI) lists it with the right host. Then send it a
postcard from another session and watch the nudge arrive. To see the
raw payload a host sends, temporarily point a hook at
`cat > /tmp/payload.json`. Please open an issue with the payload and
the CLI version if anything in this page turns out to be wrong.
