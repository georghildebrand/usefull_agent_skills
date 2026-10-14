#!/usr/bin/env python3
"""A minimal stdio MCP server for tests. Python 3.9 compatible.

One tool, touch_path(path): appends the path to $CRAFT_HOME/logs/probe-called
and returns "touched <path>". It never opens the path itself.
"""
import json
import os
import sys

TOOL = {
    "name": "touch_path",
    "description": "Record a path. Used to test the craft-guard hook.",
    "inputSchema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, msg_id = msg.get("method"), msg.get("id")
        if msg_id is None:
            continue  # notification
        if method == "initialize":
            version = msg.get("params", {}).get("protocolVersion", "2025-06-18")
            reply(msg_id, {"protocolVersion": version, "capabilities": {"tools": {}},
                           "serverInfo": {"name": "fake-craft", "version": "1"}})
        elif method == "tools/list":
            reply(msg_id, {"tools": [TOOL]})
        elif method == "tools/call":
            path = msg["params"]["arguments"]["path"]
            log = os.path.join(os.environ["CRAFT_HOME"], "logs", "probe-called")
            with open(log, "a") as f:
                f.write(path + "\n")
            reply(msg_id, {"content": [{"type": "text", "text": "touched " + path}]})
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32601, "message": "unknown method " + str(method)}}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
