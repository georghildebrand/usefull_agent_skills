"""Tests for scripts/check-confidentiality.sh."""
import os
import shutil
import unittest

from helpers import ROOT, CraftHome

SCRIPT = os.path.join(ROOT, "scripts", "check-confidentiality.sh")


class ConfidentialityTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome(extra='CRAFT_DENY_WORDS="examplecorp,Jane Roe"\n')

    def tearDown(self):
        self.h.cleanup()

    def check(self, text):
        path = os.path.join(self.h.base, "sample.md")
        with open(path, "w") as f:
            f.write(text)
        return self.h.run(SCRIPT, path)

    def test_clean_text_passes(self):
        r = self.check("Use $HOME/craft and UTF-8, SHA-256, ISO-8601.\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_home_path_found(self):
        r = self.check("see " + "/Us" + "ers/alice/notes\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("home path", r.stdout)

    def test_ticket_key_found(self):
        r = self.check("fixed in " + "ABC" + "-123\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ticket key", r.stdout)

    def test_deny_word_found_case_insensitive(self):
        r = self.check("Built at ExampleCorp.\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("deny word", r.stdout)

    def test_missing_file_is_a_failure(self):
        r = self.h.run(SCRIPT, os.path.join(self.h.base, "does-not-exist.md"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no such file", r.stderr)
        self.assertNotIn("clean", r.stdout)

    def test_git_failure_is_a_failure(self):
        # A copy of the script in a folder that is not a git repository.
        root = os.path.join(self.h.base, "fakerepo", "craft-agent")
        os.makedirs(os.path.join(root, "scripts"))
        shutil.copytree(os.path.join(ROOT, "bin"), os.path.join(root, "bin"))
        script = os.path.join(root, "scripts", "check-confidentiality.sh")
        shutil.copy(SCRIPT, script)
        r = self.h.run(script)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("cannot list files", r.stderr)
        self.assertNotIn("clean", r.stdout)

    def test_success_line_says_when_deny_words_were_not_checked(self):
        h = CraftHome()
        try:
            path = os.path.join(h.base, "ok.md")
            with open(path, "w") as f:
                f.write("plain text\n")
            r = h.run(SCRIPT, path)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("1 files clean (deny words not checked)", r.stdout)
        finally:
            h.cleanup()

    def test_success_line_plain_when_deny_words_checked(self):
        r = self.check("plain text\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 files clean\n", r.stdout)

    def test_repository_files_are_clean(self):
        # This file contains the deny words that setUp configures, so use a
        # home without deny words here.
        h = CraftHome()
        try:
            r = h.run(SCRIPT)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        finally:
            h.cleanup()


if __name__ == "__main__":
    unittest.main()
