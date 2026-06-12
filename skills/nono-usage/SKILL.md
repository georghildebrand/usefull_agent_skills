---
name: nono-usage
description: Use when setting up nono to run Claude Code securely, creating or modifying nono profiles, adding per-session filesystem permissions, or debugging why a path is blocked before a session starts.
---

# nono Usage — Setup and Profiles for Claude Code

## Overview

nono is a capability-based sandbox (Landlock on Linux, Seatbelt on macOS). A built-in `claude-code` profile exists — install the pack, build a shell wrapper with your project paths, and invoke it instead of `claude` directly.

> Runtime failures *inside* a running session → use `nono:nono-sandbox` skill instead.

## Quick Start

```bash
# Install the claude-code profile pack (once)
nono pull always-further/claude

# Verify it's there
nono profile list
nono profile show claude-code
```

## Recommended Shell Wrapper

Rather than typing all flags every time, define a shell function in `~/.zshrc` or `~/.bashrc`:

```bash
claudenono() {
  nono run \
    --profile claude-code \
    --allow-cwd \
    --allow-file /dev/tty \
    --allow-file /dev/null \
    --read-file /dev/urandom \
    --allow ~/.local/bin/ \
    --allow ~/.local/share/uv/ \
    --allow ~/.cache/uv/ \
    --allow ~/workspace/myproject \
    -- claude "$@"
}
```

Key flags explained:

| Flag | Why needed |
|---|---|
| `--profile claude-code` | Base profile from the pack |
| `--allow-cwd` | Grants read-write to current directory at invocation time |
| `--allow-file /dev/tty` | Terminal I/O (interactive prompts) |
| `--allow-file /dev/null` | Needed by many subprocesses |
| `--read-file /dev/urandom` | Randomness (TLS, UUID generation) |
| `--allow ~/.local/bin/` | uv-installed tools / pipx binaries |
| `--allow ~/.local/share/uv/` + `~/.cache/uv/` | Python environment managed by uv |

Add any project directories your agent needs to read/write.

## Ad-Hoc Per-Session Paths

For one-off sessions without modifying the wrapper:

```bash
# Add a directory just for this run
nono run --profile claude-code --allow-cwd --allow ~/other/project -- claude

# Read-only access
nono run --profile claude-code --allow-cwd --read ~/data -- claude

# Single file
nono run --profile claude-code --allow-cwd --allow-file ~/.netrc -- claude
```

## Custom Profiles

When you need the same extra permissions across all sessions:

```bash
# Generate skeleton extending claude-code
nono profile init my-claude --extends claude-code

# Edit ~/.config/nono/profiles/my-claude.json
# Validate
nono profile validate my-claude

# Compare against base
nono profile diff claude-code my-claude

# Run
nono run --profile my-claude --allow-cwd -- claude
```

Reference:
```bash
nono profile schema    # JSON Schema for editor autocompletion
nono profile guide     # Full authoring guide
```

## Diagnosing Denied Paths Before Running

```bash
nono why --path /path/to/check --op readwrite
nono why --host github.com
```

## Inspecting Capabilities From Inside a Session

```bash
cat "$NONO_CAP_FILE" | jq .    # Lists fs capabilities + net_blocked
```

## Known Gotcha

`~/.ssh/known_hosts` blocked by `deny_credentials` policy → `git push` and SSH fail inside nono. Run git operations in a normal terminal outside the sandbox.
