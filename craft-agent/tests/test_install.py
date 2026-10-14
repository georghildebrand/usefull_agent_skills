"""Tests for scripts/install.sh, uninstall.sh and clean-jobs.sh in temporary folders."""
import os
import subprocess
import tempfile
import time
import unittest
import shutil

from helpers import ROOT, CraftHome


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="craft-install-"))
        self.home = os.path.join(self.base, "craft home")
        self.claude = os.path.join(self.base, "claude")
        self.lbin = os.path.join(self.base, "localbin")
        self.link = os.path.join(ROOT, ".craft-home")
        self.saved_link = os.readlink(self.link) if os.path.islink(self.link) else None
        if self.saved_link:
            os.remove(self.link)

    def tearDown(self):
        if os.path.islink(self.link):
            os.remove(self.link)
        if self.saved_link:
            os.symlink(self.saved_link, self.link)
        shutil.rmtree(self.base, ignore_errors=True)

    def run_script(self, name, *args, **env):
        e = dict(os.environ, CLAUDE_DIR=self.claude, LOCAL_BIN=self.lbin, **env)
        e.pop("CRAFT_HOME", None)
        return subprocess.run([os.path.join(ROOT, "scripts", name), *args],
                              capture_output=True, text=True, env=e)

    def test_install_creates_links_and_config(self):
        r = self.run_script("install.sh", self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.path.realpath(self.link), os.path.realpath(self.home))
        self.assertTrue(os.path.isfile(os.path.join(self.home, "config.env")))
        agents = sorted(os.listdir(os.path.join(self.claude, "agents")))
        self.assertEqual(len(agents), 11)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "craft")))
        for b in ("craft-mcp", "craft-stage", "craft-app", "craft-guard"):
            self.assertTrue(os.path.islink(os.path.join(self.lbin, b)))
        # second run is a no-op and keeps an edited config
        with open(os.path.join(self.home, "config.env"), "a") as f:
            f.write("# edited\n")
        self.assertEqual(self.run_script("install.sh", self.home).returncode, 0)
        with open(os.path.join(self.home, "config.env")) as f:
            self.assertIn("# edited", f.read())

    def test_install_refuses_to_replace_real_file(self):
        os.makedirs(os.path.join(self.claude, "agents"))
        with open(os.path.join(self.claude, "agents", "craft-pdf.md"), "w") as f:
            f.write("mine")
        r = self.run_script("install.sh", self.home)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a symlink", r.stderr)

    def test_install_refuses_other_home_without_force(self):
        self.run_script("install.sh", self.home)
        other = os.path.join(self.base, "other")
        r = self.run_script("install.sh", other)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FORCE=1", r.stderr)
        self.assertEqual(self.run_script("install.sh", other, FORCE="1").returncode, 0)

    def test_uninstall_removes_only_own_links(self):
        self.run_script("install.sh", self.home)
        foreign = os.path.join(self.lbin, "other-tool")
        os.symlink("/bin/ls", foreign)
        r = self.run_script("uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.lbin, "craft-mcp")))
        self.assertTrue(os.path.islink(foreign))
        self.assertTrue(os.path.isdir(self.home), "uninstall keeps CRAFT_HOME data")


class CleanJobsTest(unittest.TestCase):
    def test_deletes_only_old_jobs(self):
        h = CraftHome()
        try:
            old = os.path.join(h.jobs, "2020-01-01-old")
            new = os.path.join(h.jobs, "2026-01-01-new")
            os.makedirs(old)
            os.makedirs(new)
            past = time.time() - 40 * 86400
            os.utime(old, (past, past))
            r = h.run(os.path.join(ROOT, "scripts", "clean-jobs.sh"), "30")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(old))
            self.assertTrue(os.path.exists(new))
            self.assertEqual(h.run(os.path.join(ROOT, "scripts", "clean-jobs.sh"), "x").returncode, 2)
        finally:
            h.cleanup()

    def test_newline_in_folder_name_deletes_only_that_folder(self):
        h = CraftHome()
        try:
            cwd = os.path.join(h.base, "caller")
            os.makedirs(cwd)
            victim = os.path.join(cwd, "victim")
            os.makedirs(victim)
            with open(os.path.join(victim, "keep.txt"), "w") as f:
                f.write("keep")
            old = os.path.join(h.jobs, "2020-01-01-old\nvictim")
            os.makedirs(old)
            past = time.time() - 40 * 86400
            os.utime(old, (past, past))
            r = h.run(os.path.join(ROOT, "scripts", "clean-jobs.sh"), "30", cwd=cwd)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(old))
            self.assertTrue(os.path.isfile(os.path.join(victim, "keep.txt")))
        finally:
            h.cleanup()


if __name__ == "__main__":
    unittest.main()
