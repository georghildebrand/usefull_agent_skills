from pathlib import Path

import pytest
from test_service import FakeClient

from local_llm_guard import cli, service
from local_llm_guard.service import instructions_text


def _file(tmp_path, text="the port is 8080\n"):
    f = tmp_path / "notes.txt"
    f.write_text(text)
    return str(f)


def test_parse_each_subcommand():
    p = cli.build_parser()
    a = p.parse_args(["ask", "/a", "/b", "-q", "what?"])
    assert (a.command, a.paths, a.question) == ("ask", ["/a", "/b"], "what?")
    t = p.parse_args(["task", "/a", "-i", "do it"])
    assert (t.command, t.paths, t.instruction) == ("task", ["/a"], "do it")
    e = p.parse_args(["edit", "/a", "-i", "change"])
    assert (e.command, e.path, e.instruction) == ("edit", "/a", "change")
    assert p.parse_args(["status"]).command == "status"
    assert p.parse_args(["serve"]).command == "serve"
    assert p.parse_args([]).command is None


def test_ask_prints_filtered_answer(tmp_path, capsys):
    client = FakeClient(answer="port 8080")
    code = cli.main(
        ["ask", _file(tmp_path), "-q", "which port?"], client_factory=lambda cfg: client
    )
    cap = capsys.readouterr()
    assert code == 0
    assert "port 8080" in cap.out
    assert cap.err == ""


def test_task_prints_answer(tmp_path, capsys):
    client = FakeClient(answer="done")
    code = cli.main(["task", _file(tmp_path), "-i", "summarize"], client_factory=lambda c: client)
    assert code == 0
    assert "done" in capsys.readouterr().out


def test_status_uses_service(monkeypatch, capsys):
    monkeypatch.setattr(service, "status", lambda client, cfg: "status text")
    code = cli.main(["status"], client_factory=lambda cfg: FakeClient())
    assert code == 0
    assert capsys.readouterr().out.strip() == "status text"


def test_edit_prunes_then_calls_service(monkeypatch, capsys):
    order = []
    monkeypatch.setattr(cli, "prune_backups", lambda: order.append("prune"))
    monkeypatch.setattr(
        service, "edit", lambda path, ins, client, cfg: order.append("edit") or "approved"
    )
    code = cli.main(["edit", "/a", "-i", "x"], client_factory=lambda cfg: FakeClient())
    assert code == 0 and order == ["prune", "edit"]
    assert capsys.readouterr().out.strip() == "approved"


def test_edit_survives_prune_failure(monkeypatch, capsys):
    def boom():
        raise PermissionError("denied")

    monkeypatch.setattr(cli, "prune_backups", boom)
    monkeypatch.setattr(service, "edit", lambda *a, **k: "approved")
    assert cli.main(["edit", "/a", "-i", "x"], client_factory=lambda c: FakeClient()) == 0


def test_error_result_exits_1(tmp_path, capsys):
    code = cli.main(
        ["ask", str(tmp_path / "missing.txt"), "-q", "q"], client_factory=lambda c: FakeClient()
    )
    cap = capsys.readouterr()
    assert code == 1
    assert cap.out.startswith("error:")
    assert cap.err == ""


def test_unexpected_exception_goes_to_stdout(capsys):
    def boom(cfg):
        raise RuntimeError("x" + "secret")

    code = cli.main(["ask", "/a", "-q", "q"], client_factory=boom)
    cap = capsys.readouterr()
    assert code == 1
    assert cap.out.strip() == "error: internal error (RuntimeError)"
    assert cap.err == ""


def test_bad_usage_prints_nothing_on_stderr(capsys):
    code = cli.main(["ask", "/a"])
    cap = capsys.readouterr()
    assert code == 1
    assert cap.out.startswith("error:")
    assert cap.err == ""


@pytest.mark.parametrize("argv", [[], ["serve"]])
def test_no_args_and_serve_start_server(monkeypatch, argv):
    started = []
    monkeypatch.setattr(cli.server, "main", lambda: started.append(1))
    assert cli.main(argv) == 0
    assert started == [1]


@pytest.mark.parametrize("auto", [False, True])
def test_instructions_name_the_command(auto):
    t = instructions_text(auto)
    assert "uv run --directory" in t
    assert "local-llm-guard ask" in t
    assert "local-llm-guard task" in t
    assert "local-llm-guard edit" in t
    assert service.package_dir() in t
    assert "do not retry" in t.lower()
    assert "single quotes" in t
    assert ".env" in t


def test_package_dir_is_the_project_root():
    root = Path(service.package_dir())
    assert (root / "pyproject.toml").is_file()


def test_no_home_path_in_source():
    src = Path(service.__file__).read_text() + Path(cli.__file__).read_text()
    assert "/Us" + "ers/" not in src
    assert "/ho" + "me/" not in src
