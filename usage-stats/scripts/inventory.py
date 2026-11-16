#!/usr/bin/env python3
"""Record which skills, subagents and MCP servers are installed right now.

Only names are stored. No file content, no command line, no settings value is
read into the database. The report compares this list with the usage counts to
name what is installed but never used.

Sources:
  ~/.claude/skills/<name>/                      user skills
  ~/.claude/agents/<name>.md                    user subagents
  each installed plugin: skills/, agents/, .mcp.json
  mcpServers in the Claude Code user settings   user MCP servers (names only)

Usage:
  inventory.py                    refresh the inventory table
  inventory.py --skip-user-mcp    leave out the user settings file
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import connect  # noqa: E402

CLAUDE_HOME = os.path.expanduser(os.environ.get("CLAUDE_HOME", "~/.claude"))
# The user settings file also holds tokens and e-mail addresses. Only the keys
# of its mcpServers object are read; the values never leave this function.
USER_SETTINGS = os.path.expanduser(
    os.environ.get("CLAUDE_USER_SETTINGS", "~/.claude.json")
)


def mcp_name(raw):
    """The server name as it appears in tool names: odd characters become _."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", raw)


def _dirs_with(path, marker):
    """Names of the folders under path that contain the marker file."""
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return []
    return [n for n in names if os.path.exists(os.path.join(path, n, marker))]


def _md_names(path):
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return []
    return [n[: -len(".md")] for n in names if n.endswith(".md")]


def _json_keys(path, *keys):
    """Keys of an object found by following keys in a JSON file; [] on error."""
    try:
        with open(path, encoding="utf-8") as fh:
            node = json.load(fh)
    except (OSError, ValueError):
        return []
    for key in keys:
        node = node.get(key) if isinstance(node, dict) else None
    return list(node) if isinstance(node, dict) else []


def installed_plugins(home):
    """(plugin name, install path) for each installed plugin."""
    try:
        with open(
            os.path.join(home, "plugins", "installed_plugins.json"), encoding="utf-8"
        ) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    found = []
    for key, entries in (data.get("plugins") or {}).items():
        entry = entries[0] if isinstance(entries, list) and entries else entries
        path = entry.get("installPath") if isinstance(entry, dict) else None
        if path:
            found.append((key.split("@")[0], path))
    return found


def installed_items(home=CLAUDE_HOME, user_settings=None):
    """Return a sorted list of (kind, name, source) for everything installed."""
    items = {}
    for n in _dirs_with(os.path.join(home, "skills"), "SKILL.md"):
        items[("skill", n)] = "user"
    for n in _md_names(os.path.join(home, "agents")):
        items[("subagent", n)] = "user"
    for plugin, path in installed_plugins(home):
        for n in _dirs_with(os.path.join(path, "skills"), "SKILL.md"):
            items[("skill", "%s:%s" % (plugin, n))] = "plugin " + plugin
        for n in _md_names(os.path.join(path, "agents")):
            items[("subagent", "%s:%s" % (plugin, n))] = "plugin " + plugin
        servers = _json_keys(os.path.join(path, ".mcp.json"), "mcpServers")
        servers = servers or _json_keys(os.path.join(path, ".mcp.json"))
        for n in servers:
            items[("mcp", mcp_name("plugin_%s_%s" % (plugin, n)))] = "plugin " + plugin
    if user_settings:
        for n in _json_keys(user_settings, "mcpServers"):
            items[("mcp", mcp_name(n))] = "user"
    return sorted((k, n, src) for (k, n), src in items.items())


def refresh(con, items):
    """Replace the inventory table with the given items."""
    now = datetime.now(timezone.utc).isoformat()
    con.execute("DELETE FROM inventory")
    con.executemany(
        "INSERT INTO inventory (kind, name, source, seen_at) VALUES (?,?,?,?)",
        [(k, n, src, now) for k, n, src in items],
    )
    con.commit()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip-user-mcp",
        action="store_true",
        help="do not read the user settings file for MCP server names",
    )
    args = ap.parse_args()
    items = installed_items(
        CLAUDE_HOME, None if args.skip_user_mcp else USER_SETTINGS
    )
    refresh(connect(), items)
    counts = {}
    for kind, _name, _src in items:
        counts[kind] = counts.get(kind, 0) + 1
    print(
        "inventory: "
        + ", ".join("%d %s" % (n, k) for k, n in sorted(counts.items()))
    )


if __name__ == "__main__":
    main()
