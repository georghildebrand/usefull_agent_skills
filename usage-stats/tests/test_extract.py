#!/usr/bin/env python3
"""Tests for extract.py and signals.py against a synthetic transcript.

The fixture is hand-written. Copying a real transcript into this repository
would publish real prompts, so no test ever reads ~/.claude/projects.

Run: python3 usage-stats/tests/test_extract.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "sample_session.jsonl")

# Point every write path at a throwaway directory before importing the plugin.
_TMP = tempfile.mkdtemp(prefix="usage-stats-test-")
os.environ["CLAUDE_USAGE_STATS_HOME"] = _TMP

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import common  # noqa: E402
import extract  # noqa: E402
import signals  # noqa: E402
from common import connect  # noqa: E402


class ExtractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = connect()
        extract.store(cls.con, extract.extract_file(FIXTURE))
        cls.row = cls.con.execute(
            "SELECT * FROM sessions WHERE session_id = 'fixture-s1'"
        ).fetchone()

    def test_counts_only_human_prompts(self):
        # Three human prompts. The tool_result record and the isMeta record
        # both carry role "user" and must not be counted.
        self.assertEqual(self.row["n_user_prompts"], 3)

    def test_assistant_and_token_totals(self):
        self.assertEqual(self.row["n_assistant"], 3)
        self.assertEqual(self.row["tokens_in"], 300)
        self.assertEqual(self.row["tokens_out"], 110)
        self.assertEqual(self.row["tokens_cache_read"], 10)
        self.assertEqual(self.row["tokens_cache_write"], 20)

    def test_tool_counters(self):
        self.assertEqual(self.row["n_tool_calls"], 3)
        self.assertEqual(self.row["n_edit"], 1)
        self.assertEqual(self.row["n_write"], 0)
        self.assertEqual(self.row["n_bash"], 2)
        self.assertEqual(self.row["n_commits"], 1)

    def test_first_edit_turn(self):
        # The Edit happens while answering the second prompt.
        self.assertEqual(self.row["first_edit_turn"], 2)

    def test_wall_time_includes_the_gap_active_time_does_not(self):
        # Records span 3610 seconds, but one gap of 3560 seconds exceeds
        # IDLE_GAP_SECONDS and is excluded from active time.
        self.assertAlmostEqual(self.row["wall_seconds"], 3610.0, places=3)
        self.assertAlmostEqual(self.row["active_seconds"], 50.0, places=3)

    def test_metadata(self):
        self.assertEqual(self.row["session_kind"], "bg")
        self.assertEqual(self.row["git_branch"], "main")
        self.assertEqual(self.row["ai_title"], "add retry to http client")
        self.assertEqual(self.row["repo"], "nonexistent-repo-fixture")

    def test_injected_context_is_stripped_from_the_stored_prompt(self):
        head = self.con.execute(
            "SELECT text_head FROM prompts WHERE session_id='fixture-s1' AND turn=2"
        ).fetchone()["text_head"]
        self.assertEqual(head, "no, that is wrong")

    def test_reextracting_keeps_assigned_kinds(self):
        self.con.execute(
            "UPDATE prompts SET kind='correction'"
            " WHERE session_id='fixture-s1' AND turn=2"
        )
        self.con.commit()
        extract.store(self.con, extract.extract_file(FIXTURE))
        kind = self.con.execute(
            "SELECT kind FROM prompts WHERE session_id='fixture-s1' AND turn=2"
        ).fetchone()["kind"]
        self.assertEqual(kind, "correction")


class SignalsTest(unittest.TestCase):
    def test_ratios_ignore_unclassified_prompts(self):
        rows = [
            {"kind": "task"},
            {"kind": "correction"},
            {"kind": None},
            {"kind": None},
        ]
        # Two prompts carry a kind, one of them is a correction.
        self.assertAlmostEqual(signals.kind_ratio(rows, "correction"), 0.5)
        self.assertAlmostEqual(signals.kind_ratio(rows, "steer"), 0.0)

    def test_ratio_of_empty_input_is_none(self):
        self.assertIsNone(signals.kind_ratio([], "correction"))
        self.assertIsNone(signals.kind_ratio([{"kind": None}], "correction"))

    def test_median_skips_sessions_without_an_edit(self):
        rows = [
            {"first_edit_turn": 1},
            {"first_edit_turn": 3},
            {"first_edit_turn": None},
        ]
        self.assertEqual(signals.median_first_edit_turn(rows), 2.0)
        self.assertIsNone(signals.median_first_edit_turn([{"first_edit_turn": None}]))

    BASE = {
        "tokens_out": 60000,
        "n_edit": 0,
        "n_write": 0,
        "n_commits": 0,
        "n_external_write": 0,
        "n_subagent_produced": 0,
    }

    def row(self, **changes):
        return dict(self.BASE, **changes)

    def test_zero_output_needs_tokens_and_no_result(self):
        self.assertTrue(signals.is_zero_output(self.row(), 50000))
        self.assertFalse(signals.is_zero_output(self.row(n_edit=2), 50000))
        self.assertFalse(signals.is_zero_output(self.row(tokens_out=100), 50000))

    def test_external_write_and_subagent_result_count_as_a_result(self):
        self.assertFalse(signals.is_zero_output(self.row(n_external_write=1), 50000))
        self.assertFalse(
            signals.is_zero_output(self.row(n_subagent_produced=3), 50000)
        )

    def test_session_never_measured_is_not_called_empty(self):
        # NULL columns: the row predates the counters and its transcript is gone.
        old = self.row(n_external_write=None, n_subagent_produced=None)
        self.assertFalse(signals.is_zero_output(old, 50000))
        self.assertTrue(signals.is_unmeasured(old, 50000))
        self.assertEqual(signals.result_status(old, 50000), "unmeasured")

    def test_file_edit_settles_the_result_even_without_the_new_counters(self):
        old = self.row(n_edit=1, n_external_write=None, n_subagent_produced=None)
        self.assertEqual(signals.result_status(old, 50000), "produced")
        self.assertFalse(signals.is_unmeasured(old, 50000))

    def test_summary_counts_unmeasured_sessions_separately(self):
        old = dict(
            self.row(n_external_write=None, n_subagent_produced=None),
            active_seconds=120,
            wall_seconds=0,
            session_kind=None,
            first_edit_turn=None,
        )
        summary = signals.summarise_group([old], [], 50000)
        self.assertEqual(summary["unmeasured_sessions"], 1)
        self.assertEqual(summary["unmeasured_seconds"], 120)
        self.assertEqual(summary["zero_output_sessions"], 0)


def _write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _assistant(session_id, ts, *tool_uses):
    return {
        "type": "assistant",
        "sessionId": session_id,
        "timestamp": ts,
        "message": {
            "model": "m",
            "usage": {"output_tokens": 10},
            "content": [
                {"type": "tool_use", "name": name, "input": inp}
                for name, inp in tool_uses
            ],
        },
    }


class ExternalResultTest(unittest.TestCase):
    """Writes that leave no file edit behind must count as a result."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="usage-stats-ext-")
        sid = "ext-s1"
        main = os.path.join(cls.dir, "proj", sid + ".jsonl")
        _write_jsonl(
            main,
            [
                {
                    "type": "user",
                    "sessionId": sid,
                    "timestamp": "2026-01-01T10:00:00Z",
                    "message": {"role": "user", "content": "do it"},
                },
                _assistant(
                    sid,
                    "2026-01-01T10:00:10Z",
                    ("mcp__notes__commit_episode", {}),
                    ("mcp__notes__recall", {}),  # a read
                    ("mcp__notes__todo_list", {}),  # a read
                    ("Bash", {"command": "git push origin main"}),
                    ("Bash", {"command": "git status"}),  # a read
                    ("Agent", {"prompt": "x"}),
                ),
            ],
        )
        # A subagent that edited a file and wrote to a system. Nested on purpose.
        sub = os.path.join(cls.dir, "proj", sid, "subagents", "workflows", "a.jsonl")
        _write_jsonl(
            sub,
            [
                _assistant(
                    sid,
                    "2026-01-01T10:00:20Z",
                    ("Edit", {}),
                    ("mcp__x__createJiraIssue", {}),
                    ("Read", {}),
                )
            ],
        )
        con = connect()
        extract.store(con, extract.extract_file(main))
        cls.row = con.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

    def test_mcp_writes_and_bash_pushes_count_reads_do_not(self):
        # commit_episode and git push count. recall, todo_list and
        # git status are reads.
        self.assertEqual(self.row["n_external_write"], 2)

    def test_subagent_calls_are_counted(self):
        self.assertEqual(self.row["n_subagent_calls"], 1)

    def test_subagent_results_are_summed_from_the_nested_folder(self):
        # One Edit and one createJiraIssue. Read is not a result.
        self.assertEqual(self.row["n_subagent_produced"], 2)

    def test_session_has_no_own_file_edit_yet_produced_something(self):
        self.assertEqual(self.row["n_edit"], 0)
        row = dict(self.row, tokens_out=60000)
        self.assertEqual(signals.result_status(row, 50000), "produced")


class MigrationTest(unittest.TestCase):
    def test_old_database_gets_the_new_columns_as_null(self):
        import sqlite3

        home = tempfile.mkdtemp(prefix="usage-stats-mig-")
        con = sqlite3.connect(os.path.join(home, "old.db"))
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE sessions (session_id TEXT PRIMARY KEY)")
        con.execute("INSERT INTO sessions VALUES ('old')")
        common.migrate(con)
        row = con.execute("SELECT * FROM sessions").fetchone()
        for col in common.ADDED_SESSION_COLUMNS:
            self.assertIsNone(row[col])
        # Running it twice must not fail.
        common.migrate(con)


class StateDirGuardTest(unittest.TestCase):
    """The state directory must never sit inside a git working tree."""

    CODE = "import common; common.connect(); print('opened')"

    def run_with_home(self, home):
        env = dict(
            os.environ,
            CLAUDE_USAGE_STATS_HOME=home,
            PYTHONPATH=os.path.join(os.path.dirname(HERE), "scripts"),
        )
        return subprocess.run(
            [sys.executable, "-c", self.CODE],
            env=env,
            capture_output=True,
            text=True,
        )

    def test_refuses_a_directory_inside_a_repository(self):
        repo = tempfile.mkdtemp(prefix="usage-stats-guard-repo-")
        subprocess.run(["git", "init", "-q", repo], check=True)
        result = self.run_with_home(os.path.join(repo, "sub", "state"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to run", result.stderr)

    def test_accepts_a_directory_outside_any_repository(self):
        plain = tempfile.mkdtemp(prefix="usage-stats-guard-plain-")
        result = self.run_with_home(plain)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("opened", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
