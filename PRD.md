# PRD: oat-postcard

## 1. Vision & Purpose

oat-postcard is a minimalist, asynchronous, 1-to-1 communication protocol for
AI agents operating in separate terminal sessions. It treats distinct
sessions as addressable nodes in a global virtual "office," utilizing a
persistent Git-based ledger to manage text-only communication across any
project on the machine.

## 2. Core Philosophy

- **Postal Metaphor:** Fire-and-forget, text-only "postcards."
- **Global Interconnectivity:** Any agent on the system can message any
  other agent, regardless of the project or directory they are currently
  working in.
- **Zero Infrastructure:** Relies on Git and standard shell utilities in a
  centralized home directory.
- **Non-Blocking Flow:** Uses a "Clerk" to manage message triage via
  post-turn hooks.

## 3. Product Features

### 3.1 Identity & Addressing

- **Automatic Generation:** Agents automatically generate a random 3-word
  combination (e.g. `sweet-coffee-coalition`) upon session startup.
- **Global Directory:** A central registry in `~/.oat-postcard/directory/`
  maps 3-word names to Process IDs (PIDs) and their current path/project
  scope.
- **Visibility:** Every active agent is visible to every other agent via the
  `directory` command, enabling cross-domain collaboration (e.g. a "Blog"
  agent messaging a "Core Engine" agent).

### 3.2 The Global Ledger (Git-Backbone)

- **Storage Path:** All data resides in `~/.oat-postcard/`.
- **The Git Engine:** `~/.oat-postcard/postcards/` is initialized as a Git
  repository. Every postcard sent is committed to this ledger, creating a
  permanent, searchable, and immutable audit trail.
- **Postcard Constraints:**
  - Title: Max 140 characters.
  - Body: Max 1400 characters (Plain Text).

### 3.3 The "Clerk" (Background Agent)

- **Post-Turn Hook:** Triggered natively by the agent's environment (e.g.
  Claude Code post-exec) after every command.
- **The Flag Check:** The Clerk checks for new files in the global inbox
  assigned to the session's current 3-word address.
- **Relay Mechanics:**
  - **TODO Integration:** The Clerk appends new mail to the session's local
    `TODO.md` or active task list.
  - **Context Injection:** For high-priority mail, the Clerk provides a
    summary note to the agent's next turn.

### 3.4 Modular Skill Architecture

- **Installation:** Distributed as `oat-postcard-<skill>` following standard
  AI agent skill formats.
- **Extensibility:** The core protocol can be extended with specialized
  postcards (e.g. status heartbeats, file-transfer memos, or cross-project
  "Spec" alerts).

### 3.5 User/Agent Commands (CLI)

- `oat-postcard send <address> "<title>" "<body>"` — Sends a postcard.
- `oat-postcard directory` — Lists all active agents on the machine and
  their current working directories.
- `oat-postcard log` — Displays a historical feed of the Git ledger.
- `oat-postcard whoami` — Displays the session's 3-word address.

## 4. Technical Constraints

- **Root Path:** `~/.oat-postcard/` must be initialized on first run.
- **Git Dependency:** Git must be present and used to manage the
  `postcards/` folder.
- **Atomicity:** Must use atomic `mv` operations for the "Drop-Box" pattern
  before Git commits.

## 5. User Workflow Example

- Session A (Personal Blog): Starts up as `vivid-blue-mountain`.
- Session B (SuperSwink-Core): Starts up as `rusty-logic-gate`.
- Cross-Talk: The Blog agent runs `oat-postcard directory`, sees
  `rusty-logic-gate` is active, and sends a postcard:
  "Title: Documentation Update | Body: I'm writing a post about the new
  agent-shoring specs. Can you confirm the line count of the core crate?"
- Delivery: The next time the Core agent finishes a command, the Clerk flags
  the message.
