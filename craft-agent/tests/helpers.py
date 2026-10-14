"""Shared helpers for the craft-agent tests.

Every test gets its own CRAFT_HOME in a temporary folder. The folder name
contains a space on purpose: all scripts must quote paths correctly.
"""
import os
import shutil
import socket
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")


def write_exe(path, body):
    with open(path, "w") as f:
        f.write(body)
    os.chmod(path, 0o755)


class CraftHome:
    """A throwaway CRAFT_HOME with config.env, bin/, jobs/, logs/, state/."""

    def __init__(self, read_root=None, port_base=7901, extra=""):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="craft-test-"))
        self.home = os.path.join(self.base, "craft home")
        for d in ("bin", "jobs", "logs", "state", "reviewed"):
            os.makedirs(os.path.join(self.home, d))
        self.read_root = read_root or os.path.join(self.base, "workspace")
        os.makedirs(self.read_root, exist_ok=True)
        self.write_config(port_base, extra)

    @property
    def jobs(self):
        return os.path.join(self.home, "jobs")

    def write_config(self, port_base=7901, extra=""):
        with open(os.path.join(self.home, "config.env"), "w") as f:
            f.write('CRAFT_READ_ROOT="%s"\n' % self.read_root)
            f.write("CRAFT_PORT_BASE=%d\n" % port_base)
            f.write(extra)

    def env(self, env_extra=None):
        e = dict(os.environ)
        e["CRAFT_HOME"] = self.home
        # craft-mcp refuses to start without craft-guard on PATH.
        e["PATH"] = BIN + os.pathsep + e.get("PATH", "")
        e.pop("CRAFT_JQ", None)
        if env_extra:
            e.update(env_extra)
        return e

    def run(self, script, *args, stdin=None, env_extra=None, cwd=None, timeout=60):
        path = script if os.path.isabs(script) else os.path.join(BIN, script)
        return subprocess.run(
            [path, *args], input=stdin, capture_output=True, text=True,
            env=self.env(env_extra), cwd=cwd, timeout=timeout,
        )

    def cleanup(self):
        shutil.rmtree(self.base, ignore_errors=True)


def no_readlink_dir(base):
    """A folder with a `readlink` that fails, to put first on PATH."""
    d = os.path.join(base, "no-readlink")
    os.makedirs(d, exist_ok=True)
    write_exe(os.path.join(d, "readlink"), "#!/bin/sh\nexit 1\n")
    return d


class Listener:
    """An open TCP port on 127.0.0.1, standing in for a running desktop app."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]

    def close(self):
        self.sock.close()
