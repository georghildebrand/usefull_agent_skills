from local_llm_guard.service import instructions_text


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
