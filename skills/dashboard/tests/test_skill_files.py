#!/usr/bin/env python3
"""Check that SKILL.md and the tile recipes exist and carry the fixed strings.

Run: python3 skills/dashboard/tests/test_skill_files.py
"""
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KINDS = ["todos", "sessions", "status", "jira", "statustable", "feed", "list"]


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class SkillFiles(unittest.TestCase):
    def test_frontmatter(self):
        text = read("SKILL.md")
        m = re.match(r"---\nname: dashboard\ndescription: (Use when [^\n]+)\n---\n", text)
        self.assertIsNotNone(m)

    def test_fixed_strings(self):
        text = read("SKILL.md")
        for s in ["dashboard refresh <preset> <tile|all>", "dashboard sync <preset>",
                  '"tiles.js"', '{db: {rules: [{path: "", read: "view", write: "admin"}]}, tts: {}, comments: {}}',
                  "presets.set_url", "__PRESET__", "__TITLE__", "__LAYOUT__", "\\u003c",
                  "meta/layout", "parseCommand", "plan_sync", "todostate/seen",
                  "create_or_extend_note", "check-clean.sh", "if_version"]:
            self.assertIn(s, text)

    def test_recipes(self):
        for kind in KINDS:
            text = read("tiles", kind + ".md")
            self.assertIn("## Source", text)
            self.assertIn("## Left out", text)

    def test_feed_queries(self):
        text = read("tiles", "feed.md")
        for s in ["lastmodified >=", "mention = currentUser()", "updated >=", "watcher = currentUser()",
                  "build_feed.query_time(", "build_feed.item_id(", "timeZone"]:
            self.assertIn(s, text)
        self.assertNotIn('"jira:<key>"', text, "feed ids carry the change time")

    def test_add_and_watch_steps(self):
        text = read("SKILL.md")
        for s in ["presets.layout_items(", "presets.append_to_layout(", "repo_dir='<skill dir>'",
                  "`ArtifactComments` `action: watch`", "every occurrence"]:
            self.assertIn(s, text)
        self.assertNotIn("This makes the session watch it", text)

    def test_paths_use_skill_dir(self):
        for name in ["SKILL.md"] + ["tiles/%s.md" % k for k in KINDS]:
            text = read(*name.split("/"))
            self.assertNotIn("skills/dashboard/", text, name)
            self.assertNotIn("'skills/dashboard'", text, name)


if __name__ == "__main__":
    unittest.main()
