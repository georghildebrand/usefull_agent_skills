#!/usr/bin/env python3
"""Smoke-test the built ArtCraft MCP servers through bin/craft-mcp.

    python3 tests/smoke.py [tool]

For every tool (or the one given): SKIP if its binary is not built. Otherwise
start `craft-mcp <tool>`, run initialize and tools/list, and run the tool's case
from smoke_cases.json if there is one. Uses the real CRAFT_HOME (the
.craft-home link or the CRAFT_HOME environment variable).

Case format: {"<tool>": {"setup": "<setup name or null>", "steps": [
  {"tool": "<mcp tool>", "arguments": {...}, "expect": "<text in result>",
   "expect_files": ["out/<file>"]}]}}
In arguments, "{job}", "{in}" and "{out}" are replaced with the job paths.
"""
import json
import os
import subprocess
import sys
import time

from mcp_client import McpClient, McpError

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CRAFT_MCP = os.path.join(ROOT, "bin", "craft-mcp")


def write_min_pdf(path, pages=2):
    """Write a valid PDF with empty 200x200 pages."""
    kids = " ".join("%d 0 R" % (3 + i) for i in range(pages))
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, pages)]
    objs += ["<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>"] * pages
    out = b"%PDF-1.4\n"
    offsets = []
    for n, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (n, obj)).encode()
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref)).encode()
    with open(path, "wb") as f:
        f.write(out)


SETUPS = {
    "pdf2": lambda in_dir: write_min_pdf(os.path.join(in_dir, "two-pages.pdf"), 2),
}


def craft_home():
    if os.environ.get("CRAFT_HOME"):
        return os.environ["CRAFT_HOME"]
    return os.path.realpath(os.path.join(ROOT, ".craft-home"))


def tool_keys():
    with open(os.path.join(ROOT, "bin", "tools.tsv")) as f:
        return [line.split("\t")[0] for line in f if line.strip() and not line.startswith("#")]


def fill(value, job):
    if isinstance(value, str):
        return (value.replace("{job}", job).replace("{in}", os.path.join(job, "in"))
                .replace("{out}", os.path.join(job, "out")))
    if isinstance(value, list):
        return [fill(v, job) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, job) for k, v in value.items()}
    return value


def text_of(result):
    return "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")


def smoke(key, cases, home):
    check = subprocess.run([CRAFT_MCP, "--check", key], capture_output=True, text=True)
    if check.returncode == 4:
        return "SKIP", check.stderr.strip()
    if check.returncode != 0:
        return "FAIL", check.stderr.strip()
    client = McpClient([CRAFT_MCP, key], timeout=60)
    try:
        client.initialize()
        tools = client.list_tools()
        if not tools:
            return "FAIL", "tools/list is empty"
        case = cases.get(key)
        if case is None:
            return "PASS", "%d tools (no call case)" % len(tools)
        job = os.path.join(home, "jobs", "smoke-%s-%s" % (key, time.strftime("%Y%m%d-%H%M%S")))
        os.makedirs(os.path.join(job, "in"))
        os.makedirs(os.path.join(job, "out"))
        if case.get("setup"):
            SETUPS[case["setup"]](os.path.join(job, "in"))
        for step in case["steps"]:
            result = client.call(step["tool"], fill(step["arguments"], job))
            text = text_of(result)
            if result.get("isError"):
                return "FAIL", "%s: %s" % (step["tool"], text[:300])
            if step.get("expect") and step["expect"] not in text:
                return "FAIL", "%s: %r not in %r" % (step["tool"], step["expect"], text[:300])
            for rel in step.get("expect_files", []):
                if not os.path.exists(os.path.join(job, rel)):
                    return "FAIL", "%s: missing %s" % (step["tool"], rel)
        return "PASS", "%d tools, %d call(s), job %s" % (len(tools), len(case["steps"]), job)
    except (McpError, TimeoutError, EOFError) as e:
        return "FAIL", str(e)
    finally:
        client.close()


def main(argv):
    with open(os.path.join(HERE, "smoke_cases.json")) as f:
        cases = json.load(f)
    keys = argv or tool_keys()
    home = craft_home()
    failed = False
    for key in keys:
        status, detail = smoke(key, cases, home)
        failed = failed or status == "FAIL"
        print("%-4s %-7s %s" % (status, key, detail))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
