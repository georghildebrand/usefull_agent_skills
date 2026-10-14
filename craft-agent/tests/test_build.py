"""Tests for scripts/build.sh and scripts/mark-reviewed.sh with a fake cargo."""
import os
import shutil
import subprocess
import unittest

from helpers import ROOT, CraftHome, write_exe

FAKE_CARGO = """#!/bin/bash
# fake cargo: `cargo build --release --locked [--target-dir <dir>] -p <pkg>` creates
# <target>/release/<pkg>. Like real cargo, the target folder is --target-dir, else
# CARGO_TARGET_DIR, else ./target.
: > "$CRAFT_HOME/cargo-args.out"
for a in "$@"; do printf '%s\\n' "$a" >> "$CRAFT_HOME/cargo-args.out"; done
printf '%s\\n' "${CARGO_TARGET_DIR-unset}" > "$CRAFT_HOME/cargo-target-env.out"
locked=0; pkg=""; prev=""; target=${CARGO_TARGET_DIR:-target}
for a in "$@"; do
  [ "$a" = "--locked" ] && locked=1
  [ "$prev" = "-p" ] && pkg="$a"
  [ "$prev" = "--target-dir" ] && target="$a"
  prev="$a"
done
[ "$locked" = 1 ] || exit 1
[ -f "$PWD/fail-build" ] && exit 101
mkdir -p "$target/release"
printf '#!/bin/bash\\necho built-%s\\n' "$pkg" > "$target/release/$pkg"
chmod +x "$target/release/$pkg"
"""


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.art = None
        self.h = CraftHome()
        self.art = os.path.join(self.h.base, "artcraft")
        self.repo = os.path.join(self.art, "gridcraft")
        os.makedirs(self.repo)
        git = ["git", "-C", self.repo]
        subprocess.run(git + ["init", "-q"], check=True)
        with open(os.path.join(self.repo, ".gitignore"), "w") as f:
            f.write("target/\nfail-build\n")
        subprocess.run(git + ["add", "."], check=True)
        subprocess.run(git + ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                              "commit", "-qm", "init"], check=True)
        self.head = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True,
                                   text=True, check=True).stdout.strip()
        self.h.write_config(extra='ARTCRAFT_DIR="%s"\n' % self.art)
        fakebin = os.path.join(self.h.base, "fakebin")
        os.makedirs(fakebin)
        write_exe(os.path.join(fakebin, "cargo"), FAKE_CARGO)
        self.path = fakebin + os.pathsep + os.environ["PATH"]

    def tearDown(self):
        self.h.cleanup()

    def script(self, name, *args, env_extra=None):
        env = {"PATH": self.path}
        env.update(env_extra or {})
        return self.h.run(os.path.join(ROOT, "scripts", name), *args, env_extra=env)

    def failing_git_status(self):
        """Put a git first on PATH that fails `git status` and runs the real git otherwise."""
        real = shutil.which("git")
        d = os.path.join(self.h.base, "badgit")
        os.makedirs(d)
        write_exe(os.path.join(d, "git"),
                  '#!/bin/bash\nfor a in "$@"; do [ "$a" = status ] && exit 128; done\n'
                  'exec "%s" "$@"\n' % real)
        return {"PATH": d + os.pathsep + self.path}

    def test_refuses_unreviewed_commit(self):
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 6)
        self.assertIn("make mark-reviewed TOOL=grid", r.stderr)

    def test_builds_after_review(self):
        self.assertEqual(self.script("mark-reviewed.sh", "grid").returncode, 0)
        with open(os.path.join(self.h.home, "reviewed", "gridcraft")) as f:
            self.assertEqual(f.read().strip(), self.head)
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.access(os.path.join(self.h.home, "bin", "gridcraft-cli"), os.X_OK))
        with open(os.path.join(self.h.home, "cargo-args.out")) as f:
            self.assertIn("--locked", f.read().splitlines())

    def test_refuses_dirty_tree(self):
        self.script("mark-reviewed.sh", "grid")
        with open(os.path.join(self.repo, "build.rs"), "w") as f:
            f.write("fn main() {}")
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 6)
        self.assertIn("uncommitted", r.stderr)

    def test_failed_build_keeps_old_binary(self):
        self.script("mark-reviewed.sh", "grid")
        old = os.path.join(self.h.home, "bin", "gridcraft-cli")
        write_exe(old, "#!/bin/bash\necho old\n")
        open(os.path.join(self.repo, "fail-build"), "w").close()
        r = self.script("build.sh", "grid")
        self.assertEqual(r.returncode, 7)
        with open(old) as f:
            self.assertIn("echo old", f.read())

    def test_app_kind_builds_app_package(self):
        self.script("mark-reviewed.sh", "grid")
        r = self.script("build.sh", "grid", "app")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.h.home, "bin", "gridcraft")))

    def test_ignores_cargo_target_dir(self):
        self.script("mark-reviewed.sh", "grid")
        elsewhere = os.path.join(self.h.base, "other-target")
        r = self.script("build.sh", "grid", env_extra={"CARGO_TARGET_DIR": elsewhere})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(elsewhere))
        with open(os.path.join(self.h.home, "cargo-target-env.out")) as f:
            self.assertEqual(f.read().strip(), "unset")
        with open(os.path.join(self.h.home, "cargo-args.out")) as f:
            args = f.read().splitlines()
        self.assertIn("--target-dir", args)
        self.assertEqual(args[args.index("--target-dir") + 1], os.path.join(self.repo, "target"))
        with open(os.path.join(self.h.home, "bin", "gridcraft-cli")) as f:
            self.assertIn("built-gridcraft-cli", f.read())

    def test_build_fails_closed_when_git_status_fails(self):
        self.script("mark-reviewed.sh", "grid")
        r = self.script("build.sh", "grid", env_extra=self.failing_git_status())
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn("git status failed", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.h.home, "bin", "gridcraft-cli")))

    def test_mark_reviewed_fails_closed_when_git_status_fails(self):
        r = self.script("mark-reviewed.sh", "grid", env_extra=self.failing_git_status())
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.h.home, "reviewed", "gridcraft")))


if __name__ == "__main__":
    unittest.main()
