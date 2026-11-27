#!/usr/bin/env python3
"""Build the ToDo tile document from a zotero2ai todo_list result.

Usage: build_todos.py <tool-result-file> <project> <out.json>

The tool-result file is the saved MCP output {"result": "<json string>"}, or
the todo_list result itself ({"todos": [...]}) saved as JSON.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

OPEN = {"todo", "in_progress", "blocked"}
PREFIX = re.compile(r"^\[MEM\]\[todo\]\[[^\]]*\]\s*")
TITLE_MAX = 220
DESC_MAX = 900


def build(todo_list_result, project):
    items = []
    for t in todo_list_result.get("todos", []):
        if t.get("status") not in OPEN:
            continue
        items.append({
            "key": t.get("key"),
            "title": PREFIX.sub("", t.get("title") or "")[:TITLE_MAX],
            "status": t["status"],
            "priority": t.get("priority"),
            "version": t.get("version"),
            "updatedAt": t.get("updated_at"),
            "createdAt": t.get("created_at"),
            "desc": (t.get("description") or "")[:DESC_MAX],
            "blockedReason": (t.get("blocked_reason") or "")[:300],
            "dueAt": t.get("due_at") or "",
        })
    items.sort(key=lambda i: i["updatedAt"] or "", reverse=True)
    for n, item in enumerate(items):
        item["order"] = n
    return common.fit_document(common.envelope("todos", items, project=project))


def main(argv):
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        raw = json.load(fh)
    inner = raw.get("result", raw) if isinstance(raw, dict) else raw
    data = json.loads(inner) if isinstance(inner, str) else inner
    common.write_json(argv[3], build(data, argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
