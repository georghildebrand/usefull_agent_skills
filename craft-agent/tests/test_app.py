"""Tests for bin/craft-app."""
import os
import re
import stat
import time
import unittest

from helpers import CraftHome, write_exe

FAKE_APP = """#!/bin/bash
printf '%s\\n' "$@" > "$CRAFT_HOME/app-argv.out"
"""


class AppTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome(port_base=7901)

    def tearDown(self):
        self.h.cleanup()

    def wait_argv(self):
        path = os.path.join(self.h.home, "app-argv.out")
        for _ in range(50):
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().splitlines()
            time.sleep(0.1)
        self.fail("fake app did not run")

    def test_photo_gets_port_and_token(self):
        write_exe(os.path.join(self.h.home, "bin", "photocraft"), FAKE_APP)
        r = self.h.run("craft-app", "photo")
        self.assertEqual(r.returncode, 0, r.stderr)
        token = os.path.join(self.h.home, "photo.token")
        self.assertEqual(self.wait_argv(), ["--control", "7908", "--control-token-file", token])
        self.assertEqual(stat.S_IMODE(os.stat(token).st_mode), 0o600)
        with open(token) as f:
            self.assertRegex(f.read(), re.compile(r"^[0-9a-f]{64}$"))

    def test_vector_gets_port(self):
        write_exe(os.path.join(self.h.home, "bin", "vectorcraft"), FAKE_APP)
        self.assertEqual(self.h.run("craft-app", "vector").returncode, 0)
        self.assertEqual(self.wait_argv(), ["--control", "7910"])

    def test_pdf_has_no_live_mode(self):
        r = self.h.run("craft-app", "pdf")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no live mode", r.stderr)

    def test_missing_app(self):
        r = self.h.run("craft-app", "word")
        self.assertEqual(r.returncode, 4)
        self.assertIn("make build-app TOOL=word", r.stderr)


if __name__ == "__main__":
    unittest.main()
