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
    assert client.chat("sys", "usr", {"type": "object"}).text == "hi"
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


def test_timeout_names_url_not_body():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = OllamaClient(Config(), transport=httpx.MockTransport(handler))
    with pytest.raises(OllamaError) as exc:
        client.chat("system-part", "user-part-zzzzz")
    msg = str(exc.value)
    assert "http://127.0.0.1:11434" in msg
    assert "system-part" not in msg and "user-part" not in msg


def test_client_ignores_proxy_env(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://proxy.example:3128")
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    client = OllamaClient(Config())
    with client._http() as http:
        assert http.trust_env is False
        assert not http._mounts
        for url in ("http://127.0.0.1:11434/api/chat", "http://localhost:11434/x"):
            assert http._transport_for_url(httpx.URL(url)) is http._transport


def test_proxy_env_does_not_reroute_mock_transport(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "http://proxy.example:3128")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example:3128")
    seen = {}

    def handler(request):
        seen["host"] = request.url.host
        return httpx.Response(200, json={"message": {"content": "hi"}})

    OllamaClient(Config(), transport=httpx.MockTransport(handler)).chat("s", "u")
    assert seen["host"] == "127.0.0.1"


def test_chat_sends_num_predict_and_returns_counts():
    from local_llm_guard.files import ANSWER_RESERVE

    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"message": {"content": "hi"}, "prompt_eval_count": 42, "done_reason": "stop"},
        )

    r = OllamaClient(Config(), transport=httpx.MockTransport(handler)).chat("s", "u")
    assert seen["body"]["options"]["num_predict"] == ANSWER_RESERVE
    assert (r.text, r.prompt_eval_count, r.done_reason) == ("hi", 42, "stop")


def test_checked_text_refuses_full_context_and_cut_answer():
    from local_llm_guard.files import ANSWER_RESERVE
    from local_llm_guard.ollama import ChatResult, checked_text

    assert checked_text(ChatResult("ok", 100, "stop"), 4096) == "ok"
    assert checked_text(ChatResult("ok", None, None), 4096) == "ok"
    for r in (
        ChatResult("x", 4096 - ANSWER_RESERVE, "stop"),
        ChatResult("x", 4096, "stop"),
        ChatResult("x", 10, "length"),
    ):
        with pytest.raises(OllamaError, match="^input or answer did not fit the context$"):
            checked_text(r, 4096)


def test_model_max_ctx_for_other_model():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"model_info": {"gemma3.context_length": 8192}})

    client = OllamaClient(Config(), transport=httpx.MockTransport(handler))
    assert client.model_max_ctx("gemma3:4b") == 8192
    assert seen["body"]["model"] == "gemma3:4b"


def test_checked_text_refuses_prompt_cut_by_ollama():
    # Ollama cuts a too-long prompt to about num_ctx/2 tokens and still says "stop".
    from local_llm_guard.files import estimate_tokens
    from local_llm_guard.ollama import ChatResult, checked_text

    prompt = "abc " * 4915  # estimate about 0.8 * 8192
    assert 0.79 * 8192 < estimate_tokens(prompt) < 0.81 * 8192
    with pytest.raises(OllamaError, match="^input or answer did not fit the context$"):
        checked_text(ChatResult("x", 8192 // 2 + 2, "stop"), 8192, prompt)
    assert checked_text(ChatResult("ok", 6000, "stop"), 8192, prompt) == "ok"
    # Small prompts are not checked this way: their count may be far below the estimate.
    assert checked_text(ChatResult("ok", 10, "stop"), 8192, "abc " * 100) == "ok"


def test_typical_estimate_spots_cut_for_cjk_and_code():
    from local_llm_guard.files import typical_tokens

    cjk = "".join(chr(0x4E00 + i % 2000) for i in range(400))
    assert typical_tokens(cjk) == 400  # one per non-ASCII character, not per byte
    assert typical_tokens("x" + " " * 12 + "y") == 2  # an indent run counts once
