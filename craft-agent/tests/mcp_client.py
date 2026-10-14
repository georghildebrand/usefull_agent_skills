#!/usr/bin/env python3
"""A minimal stdio MCP client for smoke tests. Python 3.9 compatible.

    python3 tests/mcp_client.py list <tool>                  list tools and schemas
    python3 tests/mcp_client.py call <tool> <name> '<json>'  call one tool

<tool> is a craft tool key (pdf, grid, ...); the server is started with
bin/craft-mcp <tool>.
"""
import json
import os
import queue
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTOCOL_VERSION = "2025-06-18"


class McpError(Exception):
    pass


class McpClient:
    def __init__(self, argv, env=None, timeout=30):
        self.timeout = timeout
        self.next_id = 1
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, env=env)
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read(self):
        try:
            line = self.lines.get(timeout=self.timeout)
        except queue.Empty:
            raise TimeoutError("no answer within %ss" % self.timeout)
        if line is None:
            err = self.proc.stderr.read() if self.proc.poll() is not None else ""
            raise EOFError("server closed stdout (exit %s) %s" % (self.proc.poll(), err[-500:]))
        return json.loads(line)

    def request(self, method, params=None):
        msg_id = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
        while True:
            msg = self._read()
            if msg.get("id") != msg_id:
                continue  # notification or log message
            if "error" in msg:
                raise McpError("%s: %s" % (method, msg["error"]))
            return msg["result"]

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "craft-smoke", "version": "1"}})
        self.notify("notifications/initialized")
        return result

    def list_tools(self):
        tools, cursor = [], None
        while True:
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main(argv):
    if len(argv) < 2 or argv[0] not in ("list", "call"):
        print(__doc__)
        return 2
    client = McpClient([os.path.join(ROOT, "bin", "craft-mcp"), argv[1]])
    try:
        client.initialize()
        if argv[0] == "list":
            for tool in client.list_tools():
                print(json.dumps({"name": tool["name"], "inputSchema": tool.get("inputSchema")}))
        else:
            print(json.dumps(client.call(argv[2], json.loads(argv[3])), indent=2))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
