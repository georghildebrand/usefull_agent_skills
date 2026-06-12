---
name: repo2ai
description: >
  Run repo2ai on a repository path and load its full contents as context for
  the current conversation. Use when asked to review, analyze, or understand
  an entire codebase that is not already in context.
---

# repo2ai — Load Repository as Context

`repo2ai` exports a git repository's contents to structured Markdown so the
result can be used as a single context block. Use it to load an unfamiliar
codebase without reading files one by one.

## When to Use

- User asks to review or audit a full repo
- Cross-repo analysis where multiple codebases need to be compared
- Onboarding to an unfamiliar project quickly
- Feeding a repo to an independent reviewer or another session

## Basic Usage

```bash
# Current directory
repo2ai --stdout | head -200   # preview first
repo2ai --stdout               # full output for context

# Specific path
repo2ai /path/to/repo --stdout

# Save to file for reuse
repo2ai /path/to/repo --output /tmp/repo-dump.md
```

## Workflow

1. Preview with `repo2ai <path> --stdout | head -200`
2. Save a full dump with `--output` when you need reuse
3. Read the output and verify the snapshot is current against git history

## Flags

| Flag | Purpose |
|------|---------|
| `--stdout` | Output to stdout (default if no other flag) |
| `--output FILE` | Save to file |
| `--clipboard` | Copy to clipboard |
| `--ignore PATTERN` | Exclude files matching pattern |
| `--max-file-size N` | Skip files larger than N bytes |
| `--exclude-meta-files` | Skip lockfiles, build artifacts |
| `--verbose` | Show included/excluded file lists on stderr |

## Notes

- Output can be large for big repos, so trim with `--max-file-size` and `--exclude-meta-files` when needed
- This is a snapshot, not live state; check currency against `git log` before acting on findings
- Binary files are skipped automatically
