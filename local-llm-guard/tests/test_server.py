from local_llm_guard.service import instructions_text


def test_ask_first_text():
    t = instructions_text(False)
    assert "only after the user says yes" in t
    assert "that one file only" in t
    assert ".env" in t


def test_direct_text():
    t = instructions_text(True)
    assert "directly" in t
    assert "only after" not in t
    assert ".env" in t


def test_server_registers_tools():
    import asyncio

    from local_llm_guard.config import Config
    from local_llm_guard.server import build_server

    mcp = build_server({"cfg": Config()})
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"local_ask", "local_task", "local_status", "local_config"} <= names
