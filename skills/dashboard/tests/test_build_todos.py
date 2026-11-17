#!/usr/bin/env python3
"""Tests for common.py and build_todos.py against a synthetic fixture.

The fixture is hand-written. No test reads real data or calls a real API.

Run: python3 skills/dashboard/tests/test_build_todos.py
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "todo_list_small.json")

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import build_todos  # noqa: E402
import common  # noqa: E402


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.loads(json.load(fh)["result"])


class BuildTodosTest(unittest.TestCase):
    def test_open_statuses_only(self):
        src = load_fixture()
        self.assertEqual(len(src["todos"]), 5)
        doc = build_todos.build(src, "sample-project")
        self.assertEqual(len(doc["items"]), 3)
        self.assertEqual(
            {i["status"] for i in doc["items"]}, {"todo", "in_progress", "blocked"}
        )
        self.assertEqual(doc["project"], "sample-project")
        for item in doc["items"]:
            self.assertNotIn("description", item)

    def test_prefix_removed(self):
        doc = build_todos.build(load_fixture(), "sample-project")
        titles = [i["title"] for i in doc["items"]]
        self.assertIn("Review the sample plan", titles)
        self.assertFalse(any(t.startswith("[MEM]") for t in titles))

    def test_title_cut_to_220(self):
        src = load_fixture()
        src["todos"][0]["title"] = "x" * 500
        doc = build_todos.build(src, "p")
        self.assertTrue(all(len(i["title"]) <= 220 for i in doc["items"]))

    def test_sorted_by_updated_desc(self):
        doc = build_todos.build(load_fixture(), "sample-project")
        stamps = [i["updatedAt"] for i in doc["items"]]
        self.assertEqual(stamps, sorted(stamps, reverse=True))
        self.assertEqual([i["order"] for i in doc["items"]], [0, 1, 2])
        self.assertIn("createdAt", doc["items"][0])

    def test_fit_document_trims(self):
        items = [{"key": str(n), "title": "t" * 1024} for n in range(600)]
        doc = common.envelope("todos", items)
        out = common.fit_document(doc)
        self.assertLess(len(json.dumps(out).encode("utf-8")), 262144)
        self.assertGreater(out["truncated"], 0)
        self.assertEqual(out["items"][0]["key"], "0")

    def test_main_accepts_wrapped_and_plain_result(self):
        import tempfile
        src = load_fixture()
        with tempfile.TemporaryDirectory() as t:
            for name, raw in (("wrapped", {"result": json.dumps(src)}), ("plain", src)):
                inp, out = os.path.join(t, name + ".json"), os.path.join(t, name + "-out.json")
                with open(inp, "w", encoding="utf-8") as fh:
                    json.dump(raw, fh)
                self.assertEqual(build_todos.main(["x", inp, "p", out]), 0)
                with open(out, encoding="utf-8") as fh:
                    self.assertEqual(len(json.load(fh)["items"]), 3, name)

    def test_envelope_fields(self):
        doc = common.envelope("todos", [], project="p")
        self.assertEqual(doc["v"], 1)
        self.assertTrue(doc["syncedAt"].endswith("Z"))
        self.assertEqual(doc["source"], "todos")
        self.assertEqual(doc["project"], "p")


if __name__ == "__main__":
    unittest.main()
