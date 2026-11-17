#!/usr/bin/env python3
"""Tests for build_sessions.py and build_jira.py against synthetic fixtures.

The fixtures are hand-written. No test reads ~/.claude or calls a real API.

Run: python3 skills/dashboard/tests/test_build_sources.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import build_jira  # noqa: E402
import build_sessions  # noqa: E402

S1 = "aaaa1111-0000-4000-8000-000000000001"
S3 = "cccc3333-0000-4000-8000-000000000003"
HOME = "/home/tester"


class SessionTests(unittest.TestCase):
    def setUp(self):
        # Copy projects so the test can set transcript mtimes freely.
        self.tmp = tempfile.mkdtemp(prefix="dash-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = os.path.join(self.tmp, "projects")
        shutil.copytree(os.path.join(FIX, "projects"), self.projects)
        self.transcript = os.path.join(self.projects, "p1", S1 + ".jsonl")

    def build(self):
        return build_sessions.build(os.path.join(FIX, "sessions"), self.projects, HOME)

    def item(self, doc, name):
        return next(i for i in doc["items"] if i["name"] == name)

    def test_session_missing_fields_fall_back(self):
        doc = self.build()
        self.assertEqual(len(doc["items"]), 3)
        it = self.item(doc, S3[:8])
        self.assertEqual(it["kind"], "")
        self.assertEqual(it["state"], "idle")
        self.assertFalse(it["hasTranscript"])
        self.assertTrue(it["lastActiveAt"].endswith("Z"))

    def test_session_last_active_uses_transcript(self):
        os.utime(self.transcript, (1795000000, 1795000000))  # 2026-11-18T11:06:40Z
        it = self.item(self.build(), "alpha work")
        self.assertTrue(it["hasTranscript"])
        self.assertEqual(it["lastActiveAt"], "2026-11-18T11:06:40Z")
        self.assertEqual(it["startedAt"], "2026-11-17T07:20:00Z")

    def test_session_last_active_without_newer_transcript(self):
        os.utime(self.transcript, (1000, 1000))
        it = self.item(self.build(), "alpha work")
        self.assertEqual(it["lastActiveAt"], "2026-11-17T07:30:00Z")  # updatedAt

    def test_session_home_replaced(self):
        doc = self.build()
        self.assertEqual(self.item(doc, "alpha work")["cwd"], "~/code/alpha")
        self.assertEqual(self.item(doc, "beta background")["cwd"], "~")
        self.assertEqual(self.item(doc, S3[:8])["cwd"], "/srv/other")
        self.assertEqual(doc["source"], "sessions")


class JiraTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIX, "jira_search.json"), encoding="utf-8") as fh:
            self.issues = json.load(fh)["issues"]
        self.doc = build_jira.build(self.issues, "me-123", "https://example.invalid", scope="demo")

    def test_jira_null_priority_is_empty(self):
        it = next(i for i in self.doc["items"] if i["key"] == "ACME-2")
        self.assertEqual(it["priority"], "")
        self.assertEqual(it["parent"], "")
        self.assertEqual(it["updatedAt"], "2026-11-16T10:00:00Z")
        self.assertEqual(self.doc["baseUrl"], "https://example.invalid/browse/")
        self.assertEqual(self.doc["scope"], "demo")

    def test_jira_base_url_ends_with_browse(self):
        # The page builds a link as baseUrl + key, so baseUrl must end with "/browse/".
        for site in ("https://example.invalid", "https://example.invalid/",
                     "https://example.invalid/browse", "https://example.invalid/browse/"):
            doc = build_jira.build(self.issues, "me-123", site)
            self.assertEqual(doc["baseUrl"], "https://example.invalid/browse/", site)
        self.assertEqual(build_jira.build([], "me-123", "")["baseUrl"], "")

    def test_jira_role(self):
        roles = {i["key"]: i["role"] for i in self.doc["items"]}
        self.assertEqual(roles, {"ACME-1": "assignee", "ACME-2": "reporter",
                                 "ACME-3": "other", "ACME-4": "other"})
        first = self.doc["items"][0]
        self.assertEqual(first["statusCat"], "indeterminate")
        self.assertEqual(first["parent"], "ACME-100")
        self.assertEqual([i["order"] for i in self.doc["items"]], [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
