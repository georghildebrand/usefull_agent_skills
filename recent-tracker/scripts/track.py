#!/usr/bin/env python3
"""PostToolUse hook: log edited files and memory writes to a JSONL file.

Reads the hook event JSON from stdin, classifies it via ordered rules,
and appends one line to ~/.claude/recent-tracker/log.jsonl.

Rules file: ~/.claude/recent-tracker/rules.json (falls back to
rules.default.json next to this script's parent directory).
Each rule: {"path": <regex>} and/or {"tool": <regex>}, plus either
"category": <str> or "ignore": true. First matching rule wins.
A rule with only "path" never matches events without a file path.

This script must never block the session: any error exits 0 silently.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

STATE_DIR = os.path.expanduser("~/.claude/recent-tracker")
LOG_FILE = os.path.join(STATE_DIR, "log.jsonl")
USER_RULES = os.path.join(STATE_DIR, "rules.json")
DEFAULT_RULES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules.default.json")

# tool_input fields that name a Zotero/memory object, in preference order
REF_FIELDS = ("title", "name", "task_summary", "summary", "session_id", "item_key", "key")


def load_rules():
    for path in (USER_RULES, DEFAULT_RULES):
        try:
            with open(path) as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return []


def classify(rules, tool_name, file_path):
    for rule in rules:
        tool_re = rule.get("tool")
        path_re = rule.get("path")
        if tool_re and not re.fullmatch(tool_re, tool_name or ""):
            continue
        if path_re:
            if not file_path or not re.fullmatch(path_re, file_path):
                continue
        if not tool_re and not path_re:
            continue
        if rule.get("ignore"):
            return None
        return rule.get("category", "other")
    return None


def git(args, cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd] + args,
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def main():
    event = json.load(sys.stdin)
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}

    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    category = classify(load_rules(), tool_name, file_path)
    if category is None:
        return

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "category": category,
        "tool": tool_name,
    }

    if file_path:
        entry["ref"] = file_path
        repo_dir = os.path.dirname(file_path) or "."
        repo = git(["rev-parse", "--show-toplevel"], repo_dir)
        if repo:
            entry["repo"] = repo
            remote = git(["remote", "get-url", "origin"], repo)
            if remote:
                entry["remote"] = remote
    else:
        for field in REF_FIELDS:
            if tool_input.get(field):
                entry["ref"] = str(tool_input[field])[:200]
                break
        else:
            entry["ref"] = tool_name
        if tool_input.get("project"):
            entry["project"] = tool_input["project"]

    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
