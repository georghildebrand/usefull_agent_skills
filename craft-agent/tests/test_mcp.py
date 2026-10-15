"""Tests for bin/craft-mcp. Fake *-cli binaries record the arguments they get."""
import os
import unittest

from helpers import HERE, CraftHome, Listener, no_readlink_dir, write_exe

OFFSETS = {"cad": 0, "design": 1, "fig": 2, "film": 3, "grid": 4, "light": 5,
           "pdf": 6, "photo": 7, "sound": 8, "vector": 9, "word": 10, "effect": 11}

FAKE_CLI = """#!/bin/bash
{ pwd -P; printf '%s\\n' "$(basename "$0")" "$@"; } > "$CRAFT_HOME/argv.out"
"""


def expected_cases():
    with open(os.path.join(HERE, "expected_argv.txt")) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                head, cmd = line.split(" | ")
                tool, mode = head.split()
                yield tool, mode, cmd.split(" ")


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()

    def tearDown(self):
        self.h.cleanup()

    def fake(self, cli):
        write_exe(os.path.join(self.h.home, "bin", cli), FAKE_CLI)

    def recorded(self):
        with open(os.path.join(self.h.home, "argv.out")) as f:
            return f.read().splitlines()

    def test_all_23_command_lines(self):
        cases = list(expected_cases())
        self.assertEqual(len(cases), 23)
        for tool, mode, expected in cases:
            with self.subTest(tool=tool, mode=mode):
                self.fake(expected[0])
                port = 0
                listener = None
                if mode == "live":
                    listener = Listener()
                    port = listener.port
                    self.h.write_config(port_base=port - OFFSETS[tool])
                try:
                    args = [tool] + (["--live"] if mode == "live" else [])
                    r = self.h.run("craft-mcp", *args)
                finally:
                    if listener:
                        listener.close()
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout, "", "launcher must print nothing on stdout")
                fill = {"{J}": self.h.jobs, "{H}": self.h.home, "{P}": str(port)}
                want = []
                for tok in expected:
                    for k, v in fill.items():
                        tok = tok.replace(k, v)
                    want.append(tok)
                got = self.recorded()
                self.assertEqual(got[0], os.path.realpath(self.h.jobs), "cwd must be the jobs folder")
                self.assertEqual(got[1:], want)

    def test_live_port_closed(self):
        self.fake("vectorcraft-cli")
        listener = Listener()
        port = listener.port
        listener.close()
        self.h.write_config(port_base=port - OFFSETS["vector"])
        r = self.h.run("craft-mcp", "vector", "--live")
        self.assertEqual(r.returncode, 3)
        self.assertIn("craft-app vector", r.stderr)
        with open(os.path.join(self.h.home, "logs", "vector.log")) as f:
            self.assertIn("not reachable", f.read())

    def test_pdf_has_no_live_mode(self):
        self.fake("pdfcraft-cli")
        r = self.h.run("craft-mcp", "pdf", "--live")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no live mode", r.stderr)

    def test_unknown_tool(self):
        r = self.h.run("craft-mcp", "excel")
        self.assertEqual(r.returncode, 2)
        self.assertIn("known: cad design", r.stderr)

    def test_missing_binary(self):
        r = self.h.run("craft-mcp", "pdf")
        self.assertEqual(r.returncode, 4)
        self.assertIn("make build TOOL=pdf", r.stderr)

    def test_check(self):
        self.assertEqual(self.h.run("craft-mcp", "--check", "pdf").returncode, 4)
        self.fake("pdfcraft-cli")
        r = self.h.run("craft-mcp", "--check", "pdf")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_usage(self):
        self.assertEqual(self.h.run("craft-mcp").returncode, 2)
        self.assertEqual(self.h.run("craft-mcp", "pdf", "--other").returncode, 2)

    def test_missing_config(self):
        os.remove(os.path.join(self.h.home, "config.env"))
        self.assertEqual(self.h.run("craft-mcp", "pdf").returncode, 5)

    def test_refuses_without_guard_on_path(self):
        self.fake("pdfcraft-cli")
        r = self.h.run("craft-mcp", "pdf", env_extra={"PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn("craft-guard not found on PATH; the agent hook cannot run", r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertFalse(os.path.exists(os.path.join(self.h.home, "argv.out")),
                         "the server must not start")

    def test_readlink_failure(self):
        d = no_readlink_dir(self.h.base)
        r = self.h.run("craft-mcp", "pdf", env_extra={"PATH": d + os.pathsep + os.environ["PATH"]})
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn("readlink", r.stderr)


if __name__ == "__main__":
    unittest.main()
