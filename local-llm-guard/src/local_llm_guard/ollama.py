"""Small client for the local Ollama HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx2 as httpx

from .config import Config
from .files import ANSWER_RESERVE

FIT_ERROR = "input or answer did not fit the context"


class OllamaError(Exception):
    """A call to Ollama failed."""


@dataclass
class ChatResult:
    text: str
    prompt_eval_count: int | None = None  # prompt tokens Ollama read, if it reported them
    done_reason: str | None = None  # "length" means the answer was cut


def checked_text(result: ChatResult, num_ctx: int) -> str:
    """Return the text, or raise when the prompt filled the context or the answer was cut."""
    count = result.prompt_eval_count
    if result.done_reason == "length" or (count is not None and count >= num_ctx - ANSWER_RESERVE):
        raise OllamaError(FIT_ERROR)
    return result.text


class Client(Protocol):
    def chat(self, system: str, user: str, json_schema: dict | None = None) -> ChatResult: ...
    def model_max_ctx(self, model: str | None = None) -> int: ...
    def list_models(self) -> list[str]: ...
    def version(self) -> str: ...


class OllamaClient:
    def __init__(self, cfg: Config, transport: httpx.BaseTransport | None = None) -> None:
        self.cfg = cfg
        self._transport = transport

    def _http(self) -> httpx.Client:
        # trust_env=False: no proxy from HTTP_PROXY/ALL_PROXY and no .netrc, so the
        # request goes straight to the loopback address.
        return httpx.Client(transport=self._transport, timeout=self.cfg.timeout_s, trust_env=False)

    def _request(
        self, method: str, path: str, body: dict | None = None, model: str | None = None
    ) -> dict:
        url = self.cfg.base_url.rstrip("/") + path
        try:
            with self._http() as http:
                resp = http.request(method, url, json=body)
        except httpx.TimeoutException:
            raise OllamaError(f"Ollama at {self.cfg.base_url} timed out") from None
        except httpx.HTTPError:
            raise OllamaError(f"Ollama not reachable at {self.cfg.base_url}") from None
        if resp.status_code == 404:
            raise OllamaError(f"model {model or self.cfg.model} not installed")
        if resp.status_code >= 400:
            raise OllamaError(f"Ollama returned HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise OllamaError("Ollama returned an invalid response") from None
        if not isinstance(data, dict):
            raise OllamaError("Ollama returned an invalid response")
        return data

    def chat(self, system: str, user: str, json_schema: dict | None = None) -> ChatResult:
        body: dict = {
            "model": self.cfg.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "num_ctx": self.cfg.num_ctx,
                "num_predict": ANSWER_RESERVE,
                "temperature": 0,
            },
        }
        if json_schema is not None:
            body["format"] = json_schema
        data = self._request("POST", "/api/chat", body)
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise OllamaError("Ollama returned no message")
        count = data.get("prompt_eval_count")
        reason = data.get("done_reason")
        return ChatResult(
            text=content,
            prompt_eval_count=count if isinstance(count, int) else None,
            done_reason=reason if isinstance(reason, str) else None,
        )

    def model_max_ctx(self, model: str | None = None) -> int:
        name = model or self.cfg.model
        data = self._request("POST", "/api/show", {"model": name}, model=name)
        info = data.get("model_info") or {}
        for key, value in info.items():
            if key.endswith(".context_length") and isinstance(value, int):
                return value
        raise OllamaError(f"cannot read the context length of model {name}")

    def list_models(self) -> list[str]:
        data = self._request("GET", "/api/tags")
        return [m["name"] for m in data.get("models", []) if "name" in m]

    def version(self) -> str:
        return str(self._request("GET", "/api/version").get("version", ""))
