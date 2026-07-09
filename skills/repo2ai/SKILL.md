---
name: repo2ai
description: >
  Run repo2ai on a repository path and load its full contents as context for
  the current conversation. Use when asked to review, analyze, or understand
  an entire codebase that is not already in context.
---

# repo2ai — Load Repository as Context

`repo2ai` exports git repo contents to structured Markdown, usable as single
context block. Loads unfamiliar codebase without reading files one by one.

## When to Use

- Review or audit full repo
- Cross-repo analysis: compare multiple codebases
- Quick onboarding to unfamiliar project
- Feed repo to independent reviewer or another session

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

1. Preview: `repo2ai <path> --stdout | head -200`
2. Save full dump with `--output` for reuse
3. Read output, verify snapshot current against git history

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

- Output large for big repos; trim with `--max-file-size` and `--exclude-meta-files`
- Snapshot, not live state; check currency against `git log` before acting on findings
- Binary files skipped automatically
