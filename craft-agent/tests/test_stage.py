"""Tests for bin/craft-stage."""
import os
import unittest

from helpers import CraftHome, no_readlink_dir


class StageTest(unittest.TestCase):
    def setUp(self):
        self.h = CraftHome()
        self.ws = self.h.read_root

    def tearDown(self):
        self.h.cleanup()

    def make(self, rel, text="data"):
        path = os.path.join(self.ws, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        return path

    def stage(self, *args):
        return self.h.run("craft-stage", *args)

    def job(self, slug="2026-01-01-test"):
        return os.path.join(self.h.jobs, slug)

    def test_copies_file_and_prints_job(self):
        src = self.make("docs/report.pdf", "pdf-bytes")
        r = self.stage("2026-01-01-test", src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), self.job())
        with open(os.path.join(self.job(), "in", "report.pdf")) as f:
            self.assertEqual(f.read(), "pdf-bytes")
        self.assertTrue(os.path.isdir(os.path.join(self.job(), "out", "_failed")))

    def test_relative_path_and_folder(self):
        self.make("photos/a.jpg")
        self.make("photos/b.jpg")
        r = self.h.run("craft-stage", "2026-01-01-test", "photos", cwd=self.ws)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.job(), "in", "photos", "b.jpg")))

    def test_no_inputs_creates_empty_job(self):
        r = self.stage("2026-01-01-new-file")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isdir(os.path.join(self.job("2026-01-01-new-file"), "in")))

    def test_space_and_umlaut_in_name(self):
        src = self.make("Bericht ä.pdf")
        r = self.stage("2026-01-01-test", src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.job(), "in", "Bericht ä.pdf")))

    def assertRefused(self, r, text):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(text, r.stderr)

    def test_refuses_secret_names(self):
        for name in (".env", "prod.env", ".env.local", "credentials", ".netrc", ".databrickscfg"):
            with self.subTest(name=name):
                self.assertRefused(self.stage("2026-01-01-test", self.make(name)), "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_refuses_path_outside_read_root(self):
        outside = os.path.join(self.h.base, "elsewhere.pdf")
        with open(outside, "w") as f:
            f.write("x")
        self.assertRefused(self.stage("2026-01-01-test", outside), "outside CRAFT_READ_ROOT")

    def test_refuses_symlink_pointing_outside(self):
        link = os.path.join(self.ws, "hosts-link")
        os.symlink("/etc/hosts", link)
        self.assertRefused(self.stage("2026-01-01-test", link), "outside CRAFT_READ_ROOT")

    def test_refuses_folder_with_secret_or_symlink(self):
        self.make("proj/a.txt")
        self.make("proj/sub/.netrc")
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "proj")), "secret")
        self.make("proj2/a.txt")
        os.symlink("/etc", os.path.join(self.ws, "proj2", "etc"))
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "proj2")), "symlink")

    def test_no_overwrite_in_existing_job(self):
        src = self.make("a/report.pdf", "first")
        self.assertEqual(self.stage("2026-01-01-test", src).returncode, 0)
        src2 = self.make("b/report.pdf", "second")
        self.assertRefused(self.stage("2026-01-01-test", src2), "already in the job")
        with open(os.path.join(self.job(), "in", "report.pdf")) as f:
            self.assertEqual(f.read(), "first")

    def test_two_inputs_with_same_name(self):
        a = self.make("a/report.pdf")
        b = self.make("b/report.pdf")
        self.assertRefused(self.stage("2026-01-01-test", a, b), "two inputs named report.pdf")
        self.assertFalse(os.path.exists(self.job()))

    def test_bad_slugs(self):
        src = self.make("report.pdf")
        for slug in ("../x", "a/b", ".hidden", "a..b", ""):
            with self.subTest(slug=slug):
                self.assertRefused(self.stage(slug, src), "job slug")

    def test_missing_file(self):
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "nope.pdf")), "not found")

    def test_refuses_secret_names_in_other_case(self):
        for real, alias in ((".env", ".ENV"), (".netrc", ".NetRC"), ("credentials", "Credentials")):
            with self.subTest(name=alias):
                self.make(real)
                r = self.stage("2026-01-01-test", os.path.join(self.ws, alias))
                self.assertRefused(r, "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_refuses_folder_with_mixed_case_secret(self):
        self.make("projc/a.txt")
        self.make("projc/.Env.local")
        self.assertRefused(self.stage("2026-01-01-test", os.path.join(self.ws, "projc")), "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_case_collision(self):
        a = self.make("p/Report.pdf", "one")
        b = self.make("q/report.pdf", "two")
        self.assertRefused(self.stage("2026-01-01-test", a, b), "two inputs named")
        self.assertFalse(os.path.exists(self.job()))

    def test_unicode_form_collision(self):
        import unicodedata
        a = self.make(unicodedata.normalize("NFC", "p/B\u00e4.pdf"))
        b = self.make(unicodedata.normalize("NFD", "q/B\u00e4.pdf"))
        self.assertRefused(self.stage("2026-01-01-test", a, b), "two inputs named")
        self.assertFalse(os.path.exists(self.job()))

    def test_collision_keeps_existing_job(self):
        self.assertEqual(self.stage("2026-01-01-test", self.make("x/keep.pdf")).returncode, 0)
        a = self.make("p/Report.pdf")
        b = self.make("q/report.pdf")
        self.assertRefused(self.stage("2026-01-01-test", a, b), "two inputs named")
        self.assertTrue(os.path.isfile(os.path.join(self.job(), "in", "keep.pdf")))
        self.assertEqual(os.listdir(os.path.join(self.job(), "in")), ["keep.pdf"])

    def test_dot_argument_uses_real_name(self):
        self.make("a/docs/x.txt", "xx")
        r = self.h.run("craft-stage", "2026-01-01-test", ".", cwd=os.path.join(self.ws, "a", "docs"))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.job(), "in", "docs", "x.txt")) as f:
            self.assertEqual(f.read(), "xx")

    def test_dot_collides_with_same_named_folder(self):
        self.make("a/docs/x.txt", "first")
        self.make("b/docs/y.txt", "second")
        r = self.h.run("craft-stage", "2026-01-01-test", os.path.join(self.ws, "a", "docs"),
                       ".", cwd=os.path.join(self.ws, "b", "docs"))
        self.assertRefused(r, "two inputs named docs")
        self.assertFalse(os.path.exists(self.job()))

    def test_dot_after_first_copy_keeps_first(self):
        self.make("a/docs/x.txt", "first")
        self.make("b/docs/y.txt", "second")
        self.assertEqual(self.stage("2026-01-01-test", os.path.join(self.ws, "a", "docs")).returncode, 0)
        r = self.h.run("craft-stage", "2026-01-01-test", ".", cwd=os.path.join(self.ws, "b", "docs"))
        self.assertRefused(r, "already in the job")
        with open(os.path.join(self.job(), "in", "docs", "x.txt")) as f:
            self.assertEqual(f.read(), "first")
        self.assertFalse(os.path.exists(os.path.join(self.job(), "in", "docs", "y.txt")))

    def test_dotdot_never_writes_into_out(self):
        self.make("a/b/x.txt")
        r = self.h.run("craft-stage", "2026-01-01-test", "..", cwd=os.path.join(self.ws, "a", "b"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.listdir(os.path.join(self.job(), "out")), ["_failed"])
        self.assertTrue(os.path.isfile(os.path.join(self.job(), "in", "a", "b", "x.txt")))

    def test_refuses_secret_via_apfs_folding(self):
        self.make("credentials")
        r = self.stage("2026-01-01-test", os.path.join(self.ws, "credential\u017f"))
        self.assertRefused(r, "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_refuses_file_inside_credentials_folder(self):
        self.make("Credentials/plain.txt")
        r = self.stage("2026-01-01-test", os.path.join(self.ws, "Credentials", "plain.txt"))
        self.assertRefused(r, "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_job_path_is_a_file(self):
        os.makedirs(self.h.jobs, exist_ok=True)
        with open(self.job("c17"), "w") as f:
            f.write("keep")
        r = self.stage("c17", self.make("first.txt"))
        self.assertRefused(r, "not a folder")
        with open(self.job("c17")) as f:
            self.assertEqual(f.read(), "keep")

    def test_failed_copy_rolls_back_in_existing_job(self):
        self.assertEqual(self.stage("2026-01-01-test", self.make("x/keep.pdf")).returncode, 0)
        first = self.make("y/first.txt")
        self.make("part/ok.txt")
        bad = self.make("part/bad.txt")
        os.chmod(bad, 0)
        def restore():
            try:
                os.chmod(bad, 0o644)
            except OSError:
                pass
        self.addCleanup(restore)
        r = self.stage("2026-01-01-test", first, os.path.join(self.ws, "part"))
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertEqual(os.listdir(os.path.join(self.job(), "in")), ["keep.pdf"])

    def lock(self, path, mode):
        os.chmod(path, mode)

        def restore():
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
        self.addCleanup(restore)

    def test_unlistable_parent_is_refused(self):
        self.make("locked/credentials")
        self.lock(os.path.join(self.ws, "locked"), 0o111)
        r = self.stage("2026-01-01-test", os.path.join(self.ws, "locked", "credential\u017f"))
        self.assertRefused(r, "secret")
        self.assertFalse(os.path.exists(self.job()))

    def test_folder_with_unreadable_subfolder_is_refused(self):
        self.make("proju/a.txt")
        self.make("proju/sub/b.txt")
        self.lock(os.path.join(self.ws, "proju", "sub"), 0)
        r = self.stage("2026-01-01-test", os.path.join(self.ws, "proju"))
        self.assertRefused(r, "cannot check folder")
        self.assertFalse(os.path.exists(self.job()))


    def test_refuses_newline_in_slug(self):
        src = self.make("report.pdf")
        for slug in ("2026-10-14-x\nvictim", "2026-10-14-x\tb", "2026-10-14-x\r"):
            with self.subTest(slug=slug):
                self.assertRefused(self.stage(slug, src), "job slug")
        self.assertEqual(os.listdir(self.h.jobs), [])

    def test_refuses_non_ascii_slug(self):
        self.assertRefused(self.stage("2026-10-14-bericht-\u00e4"), "job slug")

    def test_readlink_failure(self):
        d = no_readlink_dir(self.h.base)
        r = self.h.run("craft-stage", "2026-01-01-test",
                       env_extra={"PATH": d + os.pathsep + os.environ["PATH"]})
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertFalse(os.path.exists(self.job()))

if __name__ == "__main__":
    unittest.main()
