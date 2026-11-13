import pytest

from local_llm_guard import usage


@pytest.fixture(autouse=True)
def usage_log(tmp_path_factory, monkeypatch):
    """Every test writes its usage log to its own folder, never to the home directory."""
    path = tmp_path_factory.mktemp("usage") / "usage.jsonl"
    monkeypatch.setenv("LOCAL_LLM_GUARD_USAGE_LOG", str(path))
    monkeypatch.setattr(usage, "_front", "mcp")
    return path
