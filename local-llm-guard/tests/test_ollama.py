import json

import httpx2 as httpx
import pytest

from local_llm_guard.config import Config
from local_llm_guard.ollama import OllamaClient, OllamaError


def test_chat_sends_num_ctx_and_no_stream():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "hi"}})

    cfg = Config(num_ctx=4096)
    client = OllamaClient(cfg, transport=httpx.MockTransport(handler))
    assert client.chat("sys", "usr", {"type": "object"}) == "hi"
    assert seen["url"].endswith("/api/chat")
    assert seen["body"]["options"]["num_ctx"] == 4096
    assert seen["body"]["stream"] is False
    assert seen["body"]["format"] == {"type": "object"}


def test_chat_without_schema_has_no_format():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "x"}})

    OllamaClient(Config(), transport=httpx.MockTransport(handler)).chat("s", "u")
    assert "format" not in seen["body"]


def test_connection_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    client = OllamaClient(Config(), transport=httpx.MockTransport(handler))
    with pytest.raises(OllamaError, match="Ollama not reachable at http://127.0.0.1:11434"):
        client.chat("s", "u")


def test_model_not_installed():
    client = OllamaClient(
        Config(model="x:1b"), transport=httpx.MockTransport(lambda r: httpx.Response(404))
    )
    with pytest.raises(OllamaError, match="model x:1b not installed"):
        client.chat("s", "u")


def test_list_version_and_max_ctx():
    def handler(request):
        path = request.url.path
        if path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "a:1"}, {"name": "b:2"}]})
        if path == "/api/version":
            return httpx.Response(200, json={"version": "0.9.9"})
        return httpx.Response(200, json={"model_info": {"qwen2.context_length": 32768}})

    client = OllamaClient(Config(), transport=httpx.MockTransport(handler))
    assert client.list_models() == ["a:1", "b:2"]
    assert client.version() == "0.9.9"
    assert client.model_max_ctx() == 32768
