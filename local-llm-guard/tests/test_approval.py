import os
import subprocess
from pathlib import Path

from local_llm_guard import approval
from local_llm_guard.approval import ask_approval

OK = "button returned:Write, gave up:false\n"


def fake_run(calls, returncode=0, stdout=OK):
    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "open":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, returncode, stdout, "")

    return run


def osa_script(calls):
    c = next(c for c in calls if c[0] == "osascript")
    return c[c.index("-e") + 1]


def test_script_shows_escaped_path_and_title(monkeypatch):
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    assert ask_approval("-a\n+b", '/tmp/a "b".txt') is True
    s = osa_script(calls)
    assert 'File: /tmp/a \\"b\\".txt' in s
    assert 'local-llm-guard: change to a \\"b\\".txt' in s
    assert 'buttons {"Cancel", "Write"}' in s
    assert 'default button "Cancel"' in s
    assert "giving up after 120" in s


def test_backslash_escaped(monkeypatch):
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    ask_approval("x", "/tmp/a\\b")
    assert "File: /tmp/a\\\\b" in osa_script(calls)


def test_long_diff_still_shows_path(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    calls = []
    seen = {}

    def run(cmd, **kw):
        if cmd[0] == "open":
            p = cmd[-1]
            seen["mode"] = os.stat(p).st_mode & 0o777
            seen["text"] = Path(p).read_text()
            seen["path"] = p
        return fake_run(calls)(cmd, **kw)

    monkeypatch.setattr(approval.subprocess, "run", run)
    diff = "\n".join(f"+line{i}" for i in range(61))
    assert ask_approval(diff, "/tmp/long.txt") is True
    assert "File: /tmp/long.txt" in osa_script(calls)
    assert "line60" not in osa_script(calls)
    assert [c for c in calls if c[:2] == ["open", "-e"]]
    assert seen["mode"] == 0o600 and "line60" in seen["text"]
    assert str(tmp_path) in seen["path"]
    assert not os.path.exists(seen["path"])


def test_sixty_lines_stay_in_dialog(monkeypatch):
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    ask_approval("\n".join(f"+l{i}" for i in range(60)), "/tmp/x")
    assert "+l59" in osa_script(calls)
    assert not [c for c in calls if c[0] == "open"]


def test_failures_return_false(monkeypatch):
    for rc, out in [
        (1, "button returned:Write, gave up:false"),
        (0, "button returned:Cancel, gave up:false"),
        (0, "button returned:Write, gave up:true"),
        (0, ""),
    ]:
        calls = []
        monkeypatch.setattr(approval.subprocess, "run", fake_run(calls, rc, out))
        assert ask_approval("x", "/tmp/x") is False


def test_timeout_and_oserror_return_false(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(approval.subprocess, "run", boom)
    assert ask_approval("x", "/tmp/x") is False

    def boom2(cmd, **kw):
        raise OSError("x")

    monkeypatch.setattr(approval.subprocess, "run", boom2)
    assert ask_approval("x", "/tmp/x") is False


def test_non_darwin_returns_false_without_subprocess(monkeypatch):
    def fail(cmd, **kw):
        raise AssertionError("subprocess must not run")

    monkeypatch.setattr(approval.subprocess, "run", fail)
    monkeypatch.setattr(approval.sys, "platform", "linux")
    assert ask_approval("x", "/tmp/x") is False


def test_long_diff_temp_file_removed_when_run_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(approval.sys, "platform", "darwin")

    def boom(cmd, **kw):
        raise OSError("x")

    monkeypatch.setattr(approval.subprocess, "run", boom)
    diff = "\n".join(f"+l{i}" for i in range(61))
    assert ask_approval(diff, "/tmp/x") is False
    tmpdir = tmp_path / ".local" / "state" / "local-llm-guard" / "tmp"
    assert tmpdir.is_dir() and list(tmpdir.iterdir()) == []
