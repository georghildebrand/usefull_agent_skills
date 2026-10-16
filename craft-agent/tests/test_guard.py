"""Tests for bin/craft-guard, the PreToolUse hook of the craft agents.

Run: python3 -m unittest discover -s tests -p 'test_guard.py' -v
"""
import json
import os
import time
import unittest

from helpers import CraftHome, no_readlink_dir


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()
        self.job = os.path.join(self.h.jobs, "2026-01-01-test")
        os.makedirs(os.path.join(self.job, "in"))
        os.makedirs(os.path.join(self.job, "out"))
        with open(os.path.join(self.job, "in", "a.pdf"), "w") as f:
            f.write("x")

    def tearDown(self):
        self.h.cleanup()

    def hook(self, tool, tool_input, raw=None, env_extra=None):
        stdin = raw if raw is not None else json.dumps(
            {"tool_name": tool, "tool_input": tool_input})
        return self.h.run("craft-guard", stdin=stdin, env_extra=env_extra)

    def assertAllowed(self, r):
        self.assertEqual(r.returncode, 0, r.stderr)

    def assertBlocked(self, r, text):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(text, r.stderr)

    def test_secret_name_other_case_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open",
                                     {"path": os.path.join(self.job, "in", ".ENV")}), "secret")

    # allowed
    def test_path_in_job_folder_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__open",
                                     {"path": os.path.join(self.job, "in", "a.pdf")}))

    def test_new_output_path_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__save",
                                     {"path": os.path.join(self.job, "out", "new.pdf")}))

    def test_relative_path_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__open",
                                     {"path": "2026-01-01-test/in/a.pdf"}))

    def test_plain_text_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-word__run_command",
                                     {"command": "text.insert", "text": "Hello world", "n": 3}))

    def test_other_tool_not_checked(self):
        self.assertAllowed(self.hook("Bash", {"command": "cat /etc/hosts"}))

    def test_read_inside_home_allowed(self):
        self.assertAllowed(self.hook("Read",
                                     {"file_path": os.path.join(self.h.home, "logs", "pdf.log")}))

    # blocked: paths
    def test_absolute_path_outside_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "/etc/hosts"}), "outside")

    def test_dotdot_escape_blocked(self):
        p = os.path.join(self.job, "..", "..", "..", "etc", "hosts")
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_dotdot_into_missing_folder_blocked(self):
        p = self.job + "/missing/../../../../etc/passwd"
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "cannot be resolved")

    def test_bare_dotdot_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": ".."}), "outside")

    def test_tilde_path_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "~/notes.txt"}), "outside")

    def test_file_url_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"url": "file:///etc/hosts"}), "outside")

    def test_path_inside_json_string_blocked(self):
        params = json.dumps({"path": "/etc/hosts"})
        self.assertBlocked(self.hook("mcp__craft-fig__run_command",
                                     {"command": "file.open", "params": params}), "outside")

    def test_nested_list_path_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__combine",
                                     {"files": [os.path.join(self.job, "in", "a.pdf"), "/etc/hosts"]}),
                           "outside")

    def test_symlink_in_job_pointing_outside_blocked(self):
        os.symlink("/etc", os.path.join(self.job, "in", "etc-link"))
        p = os.path.join(self.job, "in", "etc-link", "hosts")
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_read_outside_home_blocked(self):
        self.assertBlocked(self.hook("Read", {"file_path": "/etc/hosts"}), "outside")

    # blocked: secret names
    def test_secret_name_in_job_blocked(self):
        p = os.path.join(self.job, "in", ".env")
        open(p, "w").close()
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "secret")

    def test_secret_suffix_blocked(self):
        p = os.path.join(self.job, "in", "prod.env")
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "secret")

    def test_bare_secret_name_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"name": "credentials"}), "secret")

    def test_read_netrc_in_home_blocked(self):
        r = self.hook("Read", {"file_path": os.path.join(self.h.home, ".netrc")})
        self.assertBlocked(r, "secret")

    # blocked: broken input or environment (fail closed)
    def test_invalid_json_blocked(self):
        self.assertBlocked(self.hook(None, None, raw="not json"), "not JSON")

    def test_missing_tool_name_blocked(self):
        self.assertBlocked(self.hook(None, None, raw='{"tool_input": {}}'), "no tool_name")

    def test_missing_jq_blocked(self):
        r = self.hook("mcp__craft-pdf__open", {"path": "/etc/hosts"},
                      env_extra={"CRAFT_JQ": "/nonexistent/jq"})
        self.assertBlocked(r, "jq not found")

    def test_missing_config_blocked(self):
        os.remove(os.path.join(self.h.home, "config.env"))
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "x"}), "config")

    def test_decisions_are_logged(self):
        self.hook("mcp__craft-pdf__open", {"path": "/etc/hosts"})
        with open(os.path.join(self.h.home, "logs", "guard.log")) as f:
            log = f.read()
        self.assertIn("mcp__craft-pdf__open\tdeny", log)

    # review round 1
    def _link_to_etc(self):
        os.symlink("/etc", os.path.join(self.job, "in", "lnk"))
        return os.path.join(self.job, "in", "lnk")

    def test_symlink_then_dotdot_existing_blocked(self):
        p = self._link_to_etc() + "/../hosts"
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_symlink_then_dotdot_new_file_blocked(self):
        p = self._link_to_etc() + "/../newfile"
        self.assertBlocked(self.hook("mcp__craft-pdf__save", {"path": p}), "outside")

    def test_symlink_then_dotdot_only_blocked(self):
        p = self._link_to_etc() + "/.."
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_file_url_single_slash_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"url": "file:/etc/hosts"}), "outside")

    def test_file_url_localhost_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open",
                                     {"url": "file://localhost/etc/hosts"}), "outside")

    def test_file_url_uppercase_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"url": "FILE:///etc/hosts"}), "outside")

    def test_file_url_other_host_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open",
                                     {"url": "file://example.org/etc/hosts"}), "outside")

    def test_file_url_encoded_dotdot_blocked(self):
        u = "file://" + self.job + "/%2E%2E" * 5 + "/etc/hosts"
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"url": u}), "outside")

    def test_file_url_encoded_slash_blocked(self):
        self._link_to_etc()
        u = "file://" + self.job + "/in/lnk%2F..%2Fhosts"
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"url": u}), "outside")

    def test_file_url_inside_jobs_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__open",
                                     {"url": "file://" + os.path.join(self.job, "in", "a.pdf")}))

    def test_symlink_cycle_blocked(self):
        os.symlink("b", os.path.join(self.job, "in", "a"))
        os.symlink("a", os.path.join(self.job, "in", "b"))
        stdin = json.dumps({"tool_name": "mcp__craft-pdf__open",
                            "tool_input": {"path": os.path.join(self.job, "in", "a")}})
        r = self.h.run("craft-guard", stdin=stdin, timeout=15)
        self.assertBlocked(r, "cannot be resolved")

    def test_tilde_user_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "~root/.profile"}), "outside")

    def test_object_key_path_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__combine",
                                     {"files": {"/etc/hosts": "x"}}), "outside")

    def test_object_key_inside_json_string_blocked(self):
        params = json.dumps({"/etc/hosts": 1})
        self.assertBlocked(self.hook("mcp__craft-fig__run_command",
                                     {"command": "x", "params": params}), "outside")

    # deferred minor M6: JSON inside a string inside a string
    def test_path_inside_json_two_levels_deep_blocked(self):
        # / is "/" only after decoding, so neither the raw string nor the
        # first decoding level shows a path.
        inner = '{"path": "\\u002fetc\\u002fhosts"}'
        params = json.dumps({"inner": inner})
        self.assertBlocked(self.hook("mcp__craft-fig__run_command",
                                     {"command": "x", "params": params}), "outside")

    def test_json_nested_too_deep_blocked(self):
        s = "1"
        for _ in range(6):
            s = json.dumps([s])
        self.assertBlocked(self.hook("mcp__craft-fig__run_command",
                                     {"command": "x", "params": s}), "nested too deep")

    # deferred minor M10: one decision is one log line
    def test_log_line_cannot_be_forged(self):
        forged = "/etc/hosts\n2026-01-01T00:00:00Z\tmcp__craft-pdf__open\tallow\tpaths ok"
        self.hook("mcp__craft-pdf__open", {"path": forged})
        with open(os.path.join(self.h.home, "logs", "guard.log")) as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertEqual(lines[0].count("\t"), 3, lines[0])
        self.assertIn("\tdeny\t", lines[0])

    # final review: paths inside a string (words)
    def test_path_after_space_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": " /etc/hosts"}), "outside")

    def test_path_after_newline_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "\n/etc/hosts"}), "outside")

    def test_path_in_command_text_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-sheet__execute_command",
                                     {"command": "OPEN /etc/hosts"}), "outside")

    def test_path_in_formula_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-sheet__set_cell",
                                     {"cell": "A1", "value": "='/etc/[hosts]S'!A1"}), "outside")

    def test_path_after_existing_job_path_blocked(self):
        p = os.path.join(self.job, "in", "a.pdf") + ";/etc/hosts"
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": p}), "outside")

    def test_text_with_slashes_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-word__run_command",
                                     {"command": "text.insert", "text": "Q1/Q2 sales",
                                      "other": "a / b"}))

    def test_existing_input_with_brackets_allowed(self):
        folder = os.path.join(self.job, "in", "Photos (2024)")
        os.makedirs(folder)
        open(os.path.join(folder, "img.jpg"), "w").close()
        self.assertAllowed(self.hook("mcp__craft-photo__open",
                                     {"path": os.path.join(folder, "img.jpg")}))

    def test_secret_word_in_text_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-word__run_command",
                                     {"command": "x", "text": "a=/x/credentials b"}), "secret")

    def test_secret_text_other_case_blocked(self):
        self.assertBlocked(self.hook("mcp__craft-word__run_command",
                                     {"command": "x", "text": "see My.ENV file"}), "secret")

    # final review: speed and size (a hook that times out lets the call through)
    def test_many_strings_blocked_fast(self):
        strings = ["w%d" % i for i in range(20000)] + ["/etc/hosts"]
        start = time.monotonic()
        stdin = json.dumps({"tool_name": "mcp__craft-pdf__combine",
                            "tool_input": {"files": strings}})
        r = self.h.run("craft-guard", stdin=stdin, timeout=60)
        elapsed = time.monotonic() - start
        self.assertBlocked(r, "too many strings to check")
        self.assertLess(elapsed, 5.0)

    def test_path_among_many_strings_blocked_fast(self):
        strings = ["w%d" % i for i in range(4990)] + ["OPEN /etc/hosts"]
        start = time.monotonic()
        stdin = json.dumps({"tool_name": "mcp__craft-pdf__combine",
                            "tool_input": {"files": strings}})
        r = self.h.run("craft-guard", stdin=stdin, timeout=60)
        elapsed = time.monotonic() - start
        self.assertBlocked(r, "outside")
        self.assertLess(elapsed, 5.0)

    def test_many_job_paths_allowed_in_time(self):
        out = os.path.join(self.job, "out")
        strings = [os.path.join(out, "page-%d.png" % i) for i in range(2000)]
        start = time.monotonic()
        stdin = json.dumps({"tool_name": "mcp__craft-pdf__export",
                            "tool_input": {"files": strings}})
        r = self.h.run("craft-guard", stdin=stdin, timeout=60)
        elapsed = time.monotonic() - start
        self.assertAllowed(r)
        self.assertLess(elapsed, 15.0)

    # final review: plain names, Read limits, own folder
    def test_bare_symlink_name_in_jobs_blocked(self):
        os.symlink("/etc", os.path.join(self.h.jobs, "etclink"))
        self.assertBlocked(self.hook("mcp__craft-pdf__open", {"path": "etclink"}), "outside")

    def test_bare_name_of_job_folder_allowed(self):
        self.assertAllowed(self.hook("mcp__craft-pdf__list", {"folder": "2026-01-01-test"}))

    def test_read_token_blocked(self):
        token = os.path.join(self.h.home, "photo.token")
        open(token, "w").close()
        self.assertBlocked(self.hook("Read", {"file_path": token}), "outside")

    def test_read_config_blocked(self):
        r = self.hook("Read", {"file_path": os.path.join(self.h.home, "config.env")})
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_read_state_blocked(self):
        r = self.hook("Read", {"file_path": os.path.join(self.h.home, "state", "x.db")})
        self.assertBlocked(r, "outside")

    def test_read_job_file_allowed(self):
        self.assertAllowed(self.hook("Read", {"file_path": os.path.join(self.job, "in", "a.pdf")}))

    def test_read_log_through_job_folder_allowed(self):
        p = self.job + "/../../logs/pdf.log"
        self.assertAllowed(self.hook("Read", {"file_path": p}))

    def test_readlink_failure_blocks(self):
        d = no_readlink_dir(self.h.base)
        r = self.hook("mcp__craft-pdf__open", {"path": "x"},
                      env_extra={"PATH": d + os.pathsep + os.environ["PATH"]})
        self.assertBlocked(r, "readlink")


if __name__ == "__main__":
    unittest.main()
