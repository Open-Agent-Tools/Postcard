# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security reports.

Instead, use GitHub's private vulnerability disclosure:
<https://github.com/Open-Agent-Tools/Postcard/security/advisories/new>

We'll acknowledge within a few days and work with you on a fix and
coordinated disclosure timeline.

## Scope

oat-postcard runs entirely on the local filesystem. The threat model
assumes any user account with read access to `~/.oat-postcard/` is
trusted. In particular:

- Postcards are plain JSON on disk, readable by any process running as
  the user.
- The ledger is a local git repo; anyone who can read it can replay all
  history.
- No authentication or encryption between sessions — sessions on the
  same machine trust each other.

Issues we're interested in:

- Path-traversal or injection in address/title/body fields.
- Atomicity bugs that could corrupt the ledger.
- Privilege escalation from hook scripts.

Issues we'd treat as feature requests, not security bugs:

- Adding end-to-end encryption.
- Network / cross-machine transport.
- Multi-user isolation.

## Supported versions

Only the latest `0.x` release receives fixes until a `1.0` is tagged.
