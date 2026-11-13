import json
import os
import stat

from test_service import TOKEN, FakeClient, write

from local_llm_guard import cli, service, usage
from local_llm_guard.config import Config


def _entries(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_log_path_from_env(tmp_path):
    assert usage.log_path({"LOCAL_LLM_GUARD_USAGE_LOG": str(tmp_path / "u.jsonl")}) == (
        tmp_path / "u.jsonl"
    )
    assert usage.log_path({"LOCAL_LLM_GUARD_USAGE_LOG": "off"}) is None
    assert usage.log_path({}).name == "usage.jsonl"


def test_record_appends_private_lines(usage_log):
    usage.record({"tool": "ask", "outcome": "ok"})
    usage.record({"tool": "task", "outcome": "error"})
    rows = _entries(usage_log)
    assert [r["tool"] for r in rows] == ["ask", "task"]
    assert all("ts" in r and r["front"] == "mcp" for r in rows)
    assert stat.S_IMODE(os.stat(usage_log).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(usage_log.parent).st_mode) == 0o700


def test_record_off_writes_nothing(usage_log, monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_GUARD_USAGE_LOG", "off")
    usage.record({"tool": "ask"})
    assert not usage_log.exists()


def test_record_never_raises(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("LOCAL_LLM_GUARD_USAGE_LOG", str(blocker / "usage.jsonl"))
    usage.record({"tool": "ask"})  # parent is a file: must not raise


def test_record_rotates(usage_log, monkeypatch):
    monkeypatch.setattr(usage, "MAX_BYTES", 10)
    usage.record({"tool": "ask"})
    usage.record({"tool": "task"})
    assert [r["tool"] for r in _entries(usage_log)] == ["task"]
    old = usage_log.with_name(usage_log.name + ".1")
    assert [r["tool"] for r in _entries(old)] == ["ask"]
    assert [r["tool"] for r in usage.read_entries(usage_log)] == ["ask", "task"]


def test_count_masks_and_outcome():
    text = "<NAME> and <NAME> wrote to <EMAIL>, key <SECRET_2>, new <SECRET>"
    assert usage.count_masks(text) == {"name": 2, "email": 1, "secret": 2}
    assert usage.outcome_of("error: x") == "error"
    assert usage.outcome_of("approved: file a") == "approved"
    assert usage.outcome_of("rejected: file a") == "rejected"
    assert usage.outcome_of("no change: x") == "no change"
    assert usage.outcome_of("file: /a (~3 tokens, fits)\n\nhi") == "ok"


def test_ask_logs_metadata_only(tmp_path, usage_log):
    question = "who owns it?"
    path = write(tmp_path, "a.txt", f"owner Erika Mustermann\ntoken={TOKEN}\n")
    client = FakeClient(answer="Erika Mustermann owns it", names=["Erika Mustermann"])
    client.prompt_eval_count = 40
    service.ask([path], question, client, Config())
    raw = usage_log.read_text()
    (row,) = _entries(usage_log)
    assert row["tool"] == "ask" and row["outcome"] == "ok"
    assert row["files"][0]["path"] == path and row["files"][0]["tokens"] > 0
    assert row["secrets_masked"] == 1
    assert row["prompt_tokens"] == 40
    assert row["masks"] == {"name": 1}
    assert row["model"] == "qwen2.5:14b" and isinstance(row["duration_s"], float)
    for forbidden in (TOKEN, "Erika", "Mustermann", question, "owns it"):
        assert forbidden not in raw


def test_error_is_logged_with_fixed_message(tmp_path, usage_log):
    service.ask([str(tmp_path / "missing.txt")], "q", FakeClient(), Config())
    (row,) = _entries(usage_log)
    assert row["outcome"] == "error" and row["error"]
    assert row["files"] == [{"path": str(tmp_path / "missing.txt")}]


def test_status_and_config_are_logged(usage_log):
    service.status(FakeClient(), Config())
    service.configure(FakeClient(), Config(), num_ctx=8192)
    rows = _entries(usage_log)
    assert [r["tool"] for r in rows] == ["status", "config"]
    assert rows[1]["num_ctx"] == 8192


def test_cli_marks_front_and_usage_command(tmp_path, usage_log, capsys):
    path = write(tmp_path, "a.txt", "the port is 8080\n")
    cli.main(["ask", path, "-q", "port?"], client_factory=lambda cfg: FakeClient(answer="8080"))
    assert _entries(usage_log)[0]["front"] == "cli"
    capsys.readouterr()
    assert cli.main(["usage"]) == 0
    out = capsys.readouterr().out
    assert "ask" in out and "ok 1" in out and str(usage_log) in out
    assert len(_entries(usage_log)) == 1  # the usage command logs nothing


def test_summarize_empty():
    assert "no entries" in usage.summarize([], "/x/usage.jsonl")


def test_read_entries_skips_bad_lines_and_filters_days(usage_log):
    usage_log.write_text(
        '{"ts": "2000-01-01T00:00:00Z", "tool": "ask"}\nnot json\n'
        + json.dumps({"ts": usage.now_iso(), "tool": "task"})
        + "\n"
    )
    assert [r["tool"] for r in usage.read_entries(usage_log)] == ["ask", "task"]
    assert [r["tool"] for r in usage.read_entries(usage_log, days=7)] == ["task"]
