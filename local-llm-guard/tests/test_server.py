import pytest

from local_llm_guard.service import canary_skips_file_tools, instructions_text


def test_ask_first_text():
    t = instructions_text(False)
    assert "only after the user says yes" in t
    assert "that one file only" in t
    assert "Do not call local_ask" in t
    assert ".env" in t


def test_direct_text():
    t = instructions_text(True)
    assert "Do not ask first" in t
    assert "only after" not in t
    assert ".env" in t


@pytest.mark.parametrize(
    "value",
    [
        "mcp__local-llm-guard__*",
        "mcp__local-llm-guard__local_*",
        " mcp__other__x , mcp__local-llm-guard__* ",
        ",".join(f"mcp__local-llm-guard__local_{t}" for t in ("ask", "task", "edit")),
    ],
)
def test_canary_skip_covers_file_tools(value):
    assert canary_skips_file_tools(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "*",
        "mcp__*",
        "Read",
        "mcp__local-llm-guard",
        "mcp__other__*",
        "mcp__local-llm-guard__local_ask",  # task and edit missing
        "mcp__local-llm-guard__*x",  # star not last
        "mcp__local-llm-guard__local_ask*,mcp__local-llm-guard__local_task",
    ],
)
def test_canary_skip_does_not_cover(value):
    assert not canary_skips_file_tools(value)


@pytest.mark.parametrize("auto", [False, True])
def test_direct_call_text_when_canary_skips(auto):
    t = instructions_text(auto, "mcp__local-llm-guard__*")
    assert "call the tool directly" in t
    assert "Do not call local_ask" not in t
    assert "blocked anyway" in t
    assert "uv run --directory" in t  # fallback command stays
    assert ".env" in t
    if auto:
        assert "Do not ask first. Call the tool directly" in t
    else:
        assert "Call the tool only after the user says yes" in t


@pytest.mark.parametrize("auto", [False, True])
def test_command_text_without_canary_skip(auto):
    assert instructions_text(auto, None) == instructions_text(auto)
    assert "Do not call local_ask" in instructions_text(auto, "mcp__other__*")


def test_server_registers_tools():
    import asyncio

    from local_llm_guard.config import Config
    from local_llm_guard.server import build_server

    mcp = build_server({"cfg": Config()})
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"local_ask", "local_task", "local_status", "local_config", "local_edit"}


def test_client_factory_error_is_guarded():
    import asyncio

    from local_llm_guard.config import Config
    from local_llm_guard.server import build_server

    def boom(cfg):
        raise RuntimeError("x" + "secret")

    mcp = build_server({"cfg": Config()}, client_factory=boom)
    for name, args in [
        ("local_ask", {"paths": ["/a"], "question": "q"}),
        ("local_task", {"paths": ["/a"], "instruction": "q"}),
        ("local_edit", {"path": "/a", "instruction": "q"}),
        ("local_status", {}),
        ("local_config", {"num_ctx": 4096}),
    ]:
        result = asyncio.run(mcp.call_tool(name, args))
        text = str(result)
        assert "internal error (RuntimeError)" in text
        assert "xsecret" not in text


def test_main_starts_when_prune_fails(monkeypatch, capsys):
    from local_llm_guard import server

    started = []

    class FakeServer:
        def run(self, transport):
            started.append(transport)

    def boom(*a, **k):
        raise PermissionError("denied: /some/backup/dir")

    monkeypatch.setattr(server, "prune_backups", boom)
    monkeypatch.setattr(server, "build_server", lambda holder: FakeServer())
    server.main()
    assert started == ["stdio"]
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err == ""
