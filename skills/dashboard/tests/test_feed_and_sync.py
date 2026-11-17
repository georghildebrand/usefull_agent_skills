#!/usr/bin/env python3
"""Tests for build_feed.py and plan_sync.py against synthetic fixtures.

The fixtures are hand-written. No test reads real data or calls a real API.

Run: python3 skills/dashboard/tests/test_feed_and_sync.py
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import build_feed  # noqa: E402
import plan_sync  # noqa: E402

NOW = "2026-11-17T10:00:00Z"


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def cql_items():
    return [
        {"id": "confluence:%s:%s" % (r["id"], r["lastModified"]), "kind": "page",
         "title": r["title"], "link": r["url"], "source": "confluence",
         "changedAt": r["lastModified"], "why": r["why"]}
        for r in load("confluence_cql.json")["results"]
    ]


class FeedTests(unittest.TestCase):
    def test_feed_dedup_and_order(self):
        doc = build_feed.merge(load("feed_existing.json"), cql_items(), NOW)
        ids = [i["id"] for i in doc["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [
            "confluence:1001:2026-11-16T09:00:00Z",
            "confluence:1002:2026-11-15T12:30:00Z",
            "confluence:1003:2026-11-14T08:15:00Z",
        ])
        self.assertEqual(doc["v"], 1)
        self.assertEqual(doc["syncedAt"], NOW)

    def test_feed_drops_old(self):
        doc = build_feed.merge(load("feed_existing.json"), [], NOW)
        self.assertNotIn("confluence:0900:2026-09-01T08:00:00Z",
                         [i["id"] for i in doc["items"]])
        doc = build_feed.merge(None, [], NOW)
        self.assertEqual(doc["items"], [])

    def test_since_defaults_to_7_days(self):
        self.assertEqual(build_feed.since(None, "confluence", NOW), "2026-11-10T10:00:00Z")
        marks = build_feed.markers(None, "confluence", NOW)
        self.assertEqual(build_feed.since(marks, "confluence", "2026-11-20T00:00:00Z"), NOW)
        self.assertEqual(build_feed.since(marks, "jira", NOW), "2026-11-10T10:00:00Z")


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.rows = {r["key"]: r for r in plan_sync.plan(
            load("flags.json"), load("notes.json"), load("todo_list_now.json"),
            {"TODO-1": "in_progress", "TODO-2": "todo", "TODO-3": "todo"})}

    def test_plan_changed_in_source(self):
        row = self.rows["TODO-3"]
        self.assertEqual(row["action"], "changed_in_source")
        self.assertEqual(row["from"], "in_progress")
        self.assertEqual(self.rows["TODO-1"]["action"], "transition")
        self.assertEqual(self.rows["TODO-1"]["note"], "finished in review")
        self.assertEqual(self.rows["TODO-1"]["to"], "done")

    def test_plan_blocked_needs_reason(self):
        self.assertEqual(self.rows["TODO-2"]["action"], "needs_reason")
        self.assertEqual(self.rows["TODO-9"]["action"], "unknown_key")

    def test_plan_ignores_meta_keys(self):
        self.assertNotIn("createdAt", self.rows)
        self.assertNotIn("TODO-4", self.rows)
        self.assertEqual(len(self.rows), 4)


if __name__ == "__main__":
    unittest.main()
