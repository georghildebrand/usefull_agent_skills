#!/usr/bin/env python3
"""Tests for presets.py and check-clean.sh against synthetic fixtures.

Fixtures are hand-written with fake values. No test reads a real private file.

Run: python3 skills/dashboard/tests/test_presets.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import presets  # noqa: E402

PRIVATE = os.path.join(HERE, "fixtures", "private_presets.json")
CHECK = os.path.join(ROOT, "scripts", "check-clean.sh")


def make_repo(tmp, name="work", **preset):
    d = os.path.join(tmp, "presets")
    os.makedirs(d)
    with open(os.path.join(d, name + ".json"), "w") as f:
        json.dump(preset, f)
    return tmp


class PresetTests(unittest.TestCase):
    def test_private_overrides_repo(self):
        with tempfile.TemporaryDirectory() as t:
            make_repo(t, tiles=[{"kind": "jira", "x": 0, "y": 0, "w": 1, "h": 1}],
                      sources={"jira": "<jira project keys>"}, filters={"a": 1})
            p = presets.load("work", t, PRIVATE)
            self.assertEqual(p["url"], "https://claude.ai/artifact/TESTONLY")
            self.assertEqual(p["tiles"][0]["kind"], "todos")
            self.assertEqual(p["sources"], {"jira": "ACME"})
            self.assertEqual(p["name"], "work")

    def test_private_only_preset(self):
        with tempfile.TemporaryDirectory() as t:
            p = presets.load("solo", t, PRIVATE)
            self.assertEqual(p["tiles"][0]["kind"], "note")
            self.assertEqual(p["filters"], {})
            self.assertEqual(p["sources"], {})

    def test_unknown_preset_raises(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(KeyError) as c:
                presets.load("nope", t, PRIVATE)
            self.assertIn("nope", str(c.exception))

    def test_url_none_when_missing(self):
        with tempfile.TemporaryDirectory() as t:
            make_repo(t, tiles=[])
            self.assertIsNone(presets.load("work", t, os.path.join(t, "none.json"))["url"])

    def test_set_url_creates_file(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "sub", "presets.json")
            presets.set_url("work", "https://claude.ai/artifact/TESTONLY", path)
            self.assertEqual(presets.load("work", t, path)["url"],
                             "https://claude.ai/artifact/TESTONLY")

    def test_add_tile_below_lowest(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "p.json")
            shutil_copy(PRIVATE, path)
            p = presets.add_tile("work", "feed", path)
            self.assertEqual(p["tiles"][-1], {"kind": "feed", "id": "feed", "x": 0, "y": 4, "w": 6, "h": 4})
            q = presets.add_tile("fresh", "note", path, w=3, h=2, repo_dir=t)
            self.assertEqual(q["tiles"], [{"kind": "note", "id": "note", "x": 0, "y": 0, "w": 3, "h": 2}])
            q = presets.add_tile("fresh", "note", path, w=3, h=2, repo_dir=t)
            self.assertEqual(q["tiles"][-1]["id"], "note-2", "a repeated kind gets the id the page gives it")

    def test_add_tile_on_repo_preset_keeps_repo_tiles(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "p.json")
            before = presets.load("global", ROOT, path)["tiles"]
            self.assertEqual(len(before), 6)
            presets.add_tile("global", "list", path, skill_id="demo", repo_dir=ROOT)
            after = presets.load("global", ROOT, path)["tiles"]
            self.assertEqual(len(after), 7)
            self.assertEqual(after[:6], before)
            self.assertEqual(after[6], {"kind": "list", "id": "list:demo", "x": 0, "y": 16, "w": 6, "h": 4})
            presets.add_tile("global", "note", path, repo_dir=ROOT)
            self.assertEqual(len(presets.load("global", ROOT, path)["tiles"]), 8)

    def test_layout_items_and_append(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "p.json")
            tiles = presets.load("global", ROOT, path)["tiles"]
            items = presets.layout_items(tiles + [{"kind": "list", "x": 0, "y": 0, "w": 6, "h": 4}])
            self.assertEqual([i["id"] for i in items],
                             ["todos", "jira", "sessions", "status", "statustable", "feed"],
                             "a list tile without id is left out, as on the page")
            self.assertEqual(items[0], {"id": "todos", "kind": "todos", "x": 0, "y": 0, "w": 6, "h": 4})
            out = presets.append_to_layout(items, {"kind": "jira", "id": "jira", "w": 6, "h": 4})
            self.assertEqual(out[-1], {"id": "jira-2", "kind": "jira", "x": 0, "y": 16, "w": 6, "h": 4})
            self.assertEqual(len(items), 6, "the input is not changed")
            self.assertEqual(presets.append_to_layout(None, {"kind": "note", "id": "note", "w": 3, "h": 2}),
                             [{"id": "note", "kind": "note", "x": 0, "y": 0, "w": 3, "h": 2}])
            with self.assertRaises(ValueError):
                presets.append_to_layout(out + [{"id": "list:a", "kind": "list", "x": 0, "y": 0, "w": 1, "h": 1}],
                                         {"kind": "list", "id": "list:a", "w": 6, "h": 4})

    def test_add_tile_unknown_kind_raises(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                presets.add_tile("work", "bogus", os.path.join(t, "p.json"))

    def test_add_tile_list_writes_list_id(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "p.json")
            p = presets.add_tile("work", "list", path, skill_id="demo-skill")
            self.assertEqual(p["tiles"], [{"kind": "list", "id": "list:demo-skill",
                                           "x": 0, "y": 0, "w": 6, "h": 4}])
            self.assertEqual(presets.load("work", t, path)["tiles"][0]["id"], "list:demo-skill")

    def test_add_tile_list_needs_valid_skill_id(self):
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, "p.json")
            for bad in (None, "", "..", "a/b", "x\n"):
                with self.assertRaises(ValueError, msg=repr(bad)):
                    presets.add_tile("work", "list", path, skill_id=bad)
            with self.assertRaises(ValueError):
                presets.add_tile("work", "jira", path, skill_id="demo")
            self.assertFalse(os.path.exists(path), "nothing written on error")
            presets.add_tile("work", "list", path, skill_id="demo")
            with self.assertRaises(ValueError):
                presets.add_tile("work", "list", path, skill_id="demo")
            self.assertEqual(len(presets.load("work", t, path)["tiles"]), 1)

    def test_check_clean_finds_value(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            shutil_copy(PRIVATE, priv)
            # strings under 3 characters are ignored
            os.makedirs(os.path.join(t, "skills", "dashboard"))
            self.assertNotIn("ab", presets.secret_values(priv))
            self.assertIn("ACME", presets.secret_values(priv))
            r = subprocess.run(["bash", CHECK, priv], capture_output=True, text=True,
                               env={**os.environ, "DASHBOARD_CHECK_ROOT": t, "DASHBOARD_CHECK_EXTRA": ""})
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("clean", r.stdout)
            with open(os.path.join(t, "skills", "dashboard", "x.md"), "w") as f:
                f.write("hello\nthe ACME corp\n")
            r = subprocess.run(["bash", CHECK, priv], capture_output=True, text=True,
                               env={**os.environ, "DASHBOARD_CHECK_ROOT": t, "DASHBOARD_CHECK_EXTRA": ""})
            self.assertEqual(r.returncode, 1)
            self.assertNotIn("ACME", r.stdout + r.stderr)
            self.assertIn("x.md:2", r.stdout)

    def _run_check(self, priv, root):
        return subprocess.run(["bash", CHECK, priv], capture_output=True, text=True,
                              env={**os.environ, "DASHBOARD_CHECK_ROOT": root, "DASHBOARD_CHECK_EXTRA": ""})

    def test_check_clean_fails_on_unreadable_private_file(self):
        for content in ("{bad", ""):
            with tempfile.TemporaryDirectory() as t:
                priv = os.path.join(t, "p.json")
                with open(priv, "w") as f:
                    f.write(content)
                os.makedirs(os.path.join(t, "skills", "dashboard"))
                r = self._run_check(priv, t)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("clean", r.stdout)
                self.assertNotIn("Traceback", r.stderr)

    def test_tile_kinds_are_not_secrets(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            presets.add_tile("global", "todos", priv, repo_dir=ROOT)
            presets.add_tile("global", "note", priv, repo_dir=ROOT)
            presets.set_url("global", "https://example.invalid/secretsite", priv)
            # "global" is a repo preset name, the kinds and kind ids (todos-2) are not secret.
            self.assertEqual(presets.secret_values(priv), ["https://example.invalid/secretsite"])
            os.makedirs(os.path.join(t, "skills", "dashboard"))
            with open(os.path.join(t, "skills", "dashboard", "x.md"), "w") as f:
                f.write("todos note feed list\n")
            r = self._run_check(priv, t)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("clean", r.stdout)

    def test_multiline_secret_is_checked_per_line(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            with open(priv, "w") as f:
                json.dump({"denyList": ["line1\nline2"]}, f)
            self.assertEqual(presets.secret_values(priv), ["line1", "line2"])
            os.makedirs(os.path.join(t, "skills", "dashboard"))
            with open(os.path.join(t, "skills", "dashboard", "x.md"), "w") as f:
                f.write("a\nline2 here\n")
            r = self._run_check(priv, t)
            self.assertEqual(r.returncode, 1)
            self.assertIn("x.md:2", r.stdout)

    def _write_repo_file(self, t, text):
        os.makedirs(os.path.join(t, "skills", "dashboard"), exist_ok=True)
        with open(os.path.join(t, "skills", "dashboard", "x.md"), "w") as f:
            f.write(text)

    def test_source_list_in_one_string_is_checked_per_key(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            with open(priv, "w") as f:
                json.dump({"presets": {"global": {"sources": {"jira": "QQX, ZZW;YYV  WWU"}}}}, f)
            vals = presets.secret_values(priv)
            for key in ("QQX, ZZW;YYV  WWU", "QQX", "ZZW", "YYV", "WWU"):
                self.assertIn(key, vals)
            self._write_repo_file(t, "a\nonly ZZW here\n")
            r = self._run_check(priv, t)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("x.md:2", r.stdout)

    def test_filters_split_at_commas_not_spaces(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            with open(priv, "w") as f:
                json.dump({"presets": {"global": {"filters": {"team": "red team, blue team"}}}}, f)
            self.assertEqual(presets.secret_values(priv), ["red team, blue team", "red team", "blue team"])

    def test_preset_name_and_tile_id_are_checked(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            with open(priv, "w") as f:
                json.dump({"presets": {"Quokkaproj": {"tiles": [
                    {"kind": "list", "id": "list:Wombatlist", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"kind": "note", "id": "note-2", "x": 0, "y": 4, "w": 3, "h": 2}]}}}, f)
            self.assertEqual(presets.secret_values(priv), ["Quokkaproj", "Wombatlist"])
            self._write_repo_file(t, "the quokkaproj runbook\n")
            r = self._run_check(priv, t)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertNotIn("quokkaproj", r.stdout.lower())
            self._write_repo_file(t, "see Wombatlist\n")
            self.assertEqual(self._run_check(priv, t).returncode, 1)
            self._write_repo_file(t, "list note note-2\n")
            self.assertEqual(self._run_check(priv, t).returncode, 0)

    def test_common_word_preset_matches_whole_words_only(self):
        with tempfile.TemporaryDirectory() as t:
            priv = os.path.join(t, "p.json")
            with open(priv, "w") as f:
                json.dump({"presets": {"work": {"sources": {"jira": "demo project"}}}}, f)
            subs, words = presets.secret_patterns(priv)
            self.assertEqual(subs, ["demo project"])
            self.assertEqual(words, ["work", "demo", "project"])
            self._write_repo_file(t, "network setup, projected values, demolition\n")
            self.assertEqual(self._run_check(priv, t).returncode, 0)
            self._write_repo_file(t, "the work log\n")
            self.assertEqual(self._run_check(priv, t).returncode, 1)
            with open(priv, "w") as f:
                json.dump({"allowList": ["Work", "project"],
                           "presets": {"work": {"sources": {"jira": "demo project"}}}}, f)
            self._write_repo_file(t, "the work log for this project\n")
            self.assertEqual(self._run_check(priv, t).returncode, 0)
            self._write_repo_file(t, "see the demo project\n")
            self.assertEqual(self._run_check(priv, t).returncode, 1)

    def test_check_clean_no_private_file(self):
        r = subprocess.run(["bash", CHECK, "/nonexistent/p.json"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("no private file, nothing to check", r.stdout)


def shutil_copy(src, dst):
    with open(src) as a, open(dst, "w") as b:
        b.write(a.read())


if __name__ == "__main__":
    unittest.main()
