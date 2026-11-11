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
        if cmd[0] == "ps":
            return subprocess.CompletedProcess(cmd, 1, "", "")
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
    assert 'File:   /tmp/a \\"b\\".txt' in s
    assert 'local-llm-guard: approve change to a \\"b\\".txt?' in s
    assert 'buttons {"Cancel", "Write"}' in s
    assert 'default button "Cancel"' in s
    assert "giving up after 120" in s


def test_backslash_escaped(monkeypatch):
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    ask_approval("x", "/tmp/a\\b")
    assert "File:   /tmp/a\\\\b" in osa_script(calls)


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
    assert "File:   /tmp/long.txt" in osa_script(calls)
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


WARN = "[Warning: this change touches a line with a secret value.]"


def test_warning_line_on_top(monkeypatch):
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    assert ask_approval("-a\n+b", "/tmp/x", True) is True
    s = osa_script(calls)
    assert s.startswith(
        'display dialog "' + WARN + "\n\nClaude wants to change a file on your Mac."
    )
    assert "giving up after 120" in s
    calls.clear()
    ask_approval("-a\n+b", "/tmp/x", False)
    assert WARN not in osa_script(calls)


def _goes_to_textedit(monkeypatch, tmp_path, diff):
    monkeypatch.setenv("HOME", str(tmp_path))
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    assert ask_approval(diff, "/tmp/x") is True
    return bool([c for c in calls if c[:2] == ["open", "-e"]]), osa_script(calls)


def test_long_line_goes_to_textedit(monkeypatch, tmp_path):
    opened, script = _goes_to_textedit(monkeypatch, tmp_path, "+" + "y" * 200 + "z")
    assert opened and "yz" not in script and "TextEdit" in script


def test_many_characters_go_to_textedit(monkeypatch, tmp_path):
    diff = "\n".join("+" + "c" * 99 for _ in range(41))  # 41 lines, over 4000 characters
    opened, script = _goes_to_textedit(monkeypatch, tmp_path, diff)
    assert opened and "c" * 99 not in script


def test_diff_at_limits_stays_in_dialog(monkeypatch, tmp_path):
    diff = "\n".join(["+" + "d" * 199] + ["+e"] * 59)  # 60 lines, 200-char line, < 4000 chars
    assert len(diff) <= 4000
    opened, script = _goes_to_textedit(monkeypatch, tmp_path, diff)
    assert not opened and "d" * 199 in script


def test_textedit_failure_returns_false_without_dialog(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(approval.sys, "platform", "darwin")
    diff = "\n".join(f"+l{i}" for i in range(61))
    for mode in ("rc", "raise"):
        calls = []

        def run(cmd, calls=calls, mode=mode, **kw):
            calls.append(cmd)
            if cmd[0] == "open":
                if mode == "raise":
                    raise OSError("x")
                return subprocess.CompletedProcess(cmd, 1, "", "")
            return subprocess.CompletedProcess(cmd, 0, OK, "")

        monkeypatch.setattr(approval.subprocess, "run", run)
        assert ask_approval(diff, "/tmp/x") is False
        assert not [c for c in calls if c[0] == "osascript"]
        tmpdir = tmp_path / ".local" / "state" / "local-llm-guard" / "tmp"
        assert list(tmpdir.iterdir()) == []


def _text(script):
    return (
        script.split('display dialog "', 1)[1]
        .split('" with title', 1)[0]
        .replace("\\n", "\n")
        .replace('\\"', '"')
    )


def _dialog(monkeypatch, diff, path="/tmp/x.txt", **kw):
    calls = []
    monkeypatch.setattr(approval.subprocess, "run", fake_run(calls))
    assert ask_approval(diff, path, **kw) is True
    return osa_script(calls)


DIFF = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n"


def test_descriptive_text(monkeypatch):
    s = _dialog(monkeypatch, DIFF, timeout_s=90)
    assert 'with title "local-llm-guard: approve change to x.txt?"' in s
    assert _text(s) == (
        "Claude wants to change a file on your Mac.\n"
        "Only you can approve it. Claude cannot press these buttons.\n\n"
        f"Request from: local-llm-guard (MCP server, process {os.getpid()})\n\n"
        "File:   /tmp/x.txt\n"
        "Change: 1 line removed, 1 line added\n"
        'Lines starting with "-" are removed, lines starting with "+" are added.\n\n'
        "@@ -1 +1 @@\n-old\n+new\n\n"
        "Write  = save this change. A backup is made first.\n"
        "Cancel = change nothing. No answer within 90 seconds counts as Cancel."
    )
    assert "giving up after 90" in s


def test_headers_removed_hunk_kept(monkeypatch):
    t = _text(_dialog(monkeypatch, DIFF))
    assert "--- a/x" not in t and "+++ b/x" not in t and "@@ -1 +1 @@" in t


def test_counts_plural_and_dashdash_line(monkeypatch):
    diff = "--- a\n+++ b\n@@ -1,3 +1,2 @@\n--- note\n-x\n+y\n ctx\n"
    t = _text(_dialog(monkeypatch, diff))
    assert "Change: 2 lines removed, 1 line added" in t
    assert "--- note" in t


def test_warning_first_then_empty_line(monkeypatch):
    t = _text(_dialog(monkeypatch, DIFF, warning=True))
    assert t.startswith(WARN + "\n\nClaude wants")


def test_textedit_text_and_counts(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    diff = "--- a\n+++ b\n@@ -1 +1,70 @@\n-a\n" + "\n".join(f"+l{i}" for i in range(70))
    t = _text(_dialog(monkeypatch, diff))
    assert "Change: 1 line removed, 70 lines added" in t
    assert "The change is long. The full change is open in TextEdit." in t
    assert "+l5" not in t
    assert t.endswith("No answer within 120 seconds counts as Cancel.")


def _ps_table(monkeypatch, table):
    """table: pid -> (ppid, comm). Missing pid = ps failure. Returns osascript call list."""
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "ps":
            pid = int(cmd[-1])
            if pid not in table:
                return subprocess.CompletedProcess(cmd, 1, "", "")
            return subprocess.CompletedProcess(cmd, 0, f"  {table[pid][0]} {table[pid][1]}\n", "")
        return subprocess.CompletedProcess(cmd, 0, OK, "")

    monkeypatch.setattr(approval.subprocess, "run", run)
    monkeypatch.setattr(approval.os, "getppid", lambda: 100)
    return calls


def _requester(monkeypatch, table):
    calls = _ps_table(monkeypatch, table)
    assert ask_approval(DIFF, "/tmp/x.txt") is True
    return next(l for l in _text(osa_script(calls)).splitlines() if l.startswith("Request from"))


def test_requester_claude_ancestor_at_level_2(monkeypatch):
    table = {100: (200, "/bin/uv"), 200: (300, "/opt/bin/Claude"), 300: (1, "/sbin/launchd")}
    line = _requester(monkeypatch, table)
    assert line == (
        f"Request from: local-llm-guard (MCP server, process {os.getpid()}), "
        "started by Claude (process 200)"
    )


def test_requester_falls_back_to_immediate_parent(monkeypatch):
    table = {100: (200, "/bin/uv"), 200: (300, "/bin/zsh"), 300: (1, "/sbin/launchd"), 1: (0, "x")}
    assert _requester(monkeypatch, table).endswith("started by uv (process 100)")


def test_requester_ps_failure_gives_own_pid_only(monkeypatch):
    line = _requester(monkeypatch, {})
    assert line == f"Request from: local-llm-guard (MCP server, process {os.getpid()})"


def test_requester_quote_in_name_is_escaped(monkeypatch):
    calls = _ps_table(monkeypatch, {100: (1, '/bin/we"ird')})
    assert ask_approval(DIFF, "/tmp/x.txt") is True
    assert 'started by we\\"ird (process 100)' in osa_script(calls)
