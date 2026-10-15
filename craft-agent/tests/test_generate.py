"""Tests for scripts/generate.py."""
import copy
import importlib.util
import os
import subprocess
import sys
import unittest

try:
    import yaml
except ImportError:
    yaml = None

from helpers import ROOT

_spec = importlib.util.spec_from_file_location("generate", os.path.join(ROOT, "scripts", "generate.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self.tools = gen.load_tools(os.path.join(ROOT, "tools.toml"))
        with open(os.path.join(ROOT, "templates", "agent.md.tmpl")) as f:
            self.template = f.read()

    def test_committed_files_match_generator(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "generate.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_twelve_valid_tools(self):
        self.assertEqual(len(self.tools), 12)
        gen.validate(self.tools)

    def test_duplicate_port_offset_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["pdf"]["port_offset"] = tools["cad"]["port_offset"]
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_token_with_space_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["cad"]["headless"] = ["mcp", "--x y"]
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_unknown_placeholder_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["cad"]["headless"] = ["mcp", "{nope}"]
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_live_without_app_args_rejected(self):
        tools = copy.deepcopy(self.tools)
        tools["cad"]["app_args"] = []
        with self.assertRaises(ValueError):
            gen.validate(tools)

    def test_headless_only_agent(self):
        text = gen.render_agent("pdf", self.tools["pdf"], self.template)
        self.assertIn("  - craft-pdf:\n", text)
        self.assertNotIn("craft-pdf-live", text)
        self.assertIn("tools: mcp__craft-pdf__*, Read", text)
        self.assertNotIn("{{", text)

    def test_live_agent_has_two_servers(self):
        text = gen.render_agent("vector", self.tools["vector"], self.template)
        self.assertIn("  - craft-vector-live:\n", text)
        self.assertIn('args: ["vector", "--live"]', text)
        self.assertIn("craft-app vector", text)

    def test_grid_agent_is_named_craft_sheet(self):
        text = gen.render_agent("grid", self.tools["grid"], self.template)
        self.assertIn("name: craft-sheet\n", text)
        self.assertIn('args: ["grid"]', text)

    def test_tsv_row(self):
        row = gen.tsv_row("pdf", self.tools["pdf"]).split("\t")
        self.assertEqual(row, ["pdf", "pdfcraft", "pdfcraft-cli", "pdfcraft", "6",
                               "mcp --root {jobs} --compact", "-", "-", "-"])

    @unittest.skipUnless(yaml, "PyYAML not installed")
    def test_frontmatter_is_valid_yaml(self):
        for key, t in self.tools.items():
            text = gen.render_agent(key, t, self.template)
            front = text.split("---\n")[1]
            fm = yaml.safe_load(front)
            self.assertEqual(fm["name"], t["agent"])
            self.assertTrue(fm["description"].endswith("/craft skill, which prepares the job folder."), key)
            self.assertEqual(fm["model"], "sonnet")
            self.assertIn("mcp__%s__*" % t["agent"], fm["tools"])
            self.assertIsInstance(fm["mcpServers"], list)
            first = fm["mcpServers"][0]
            self.assertEqual(list(first), [t["agent"]])
            self.assertEqual(first[t["agent"]]["command"], "craft-mcp")
            self.assertEqual(len(fm["mcpServers"]), 2 if t["live"] else 1)
            self.assertEqual(fm["hooks"]["PreToolUse"][0]["hooks"][0]["command"], "craft-guard")


if __name__ == "__main__":
    unittest.main()
