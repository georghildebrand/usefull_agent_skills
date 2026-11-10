"""Small client for the local Ollama HTTP API."""

from __future__ import annotations

from typing import Protocol

import httpx2 as httpx

from .config import Config


class OllamaError(Exception):
    """A call to Ollama failed."""


class Client(Protocol):
    def chat(self, system: str, user: str, json_schema: dict | None = None) -> str: ...
    def model_max_ctx(self) -> int: ...
    def list_models(self) -> list[str]: ...
    def version(self) -> str: ...


class OllamaClient:
    def __init__(self, cfg: Config, transport: httpx.BaseTransport | None = None) -> None:
        self.cfg = cfg
        self._transport = transport

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = self.cfg.base_url.rstrip("/") + path
        try:
            with httpx.Client(transport=self._transport, timeout=self.cfg.timeout_s) as http:
                resp = http.request(method, url, json=body)
        except httpx.TimeoutException:
            raise OllamaError(f"Ollama at {self.cfg.base_url} timed out") from None
        except httpx.HTTPError:
            raise OllamaError(f"Ollama not reachable at {self.cfg.base_url}") from None
        if resp.status_code == 404:
            raise OllamaError(f"model {self.cfg.model} not installed")
        if resp.status_code >= 400:
            raise OllamaError(f"Ollama returned HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise OllamaError("Ollama returned an invalid response") from None
        if not isinstance(data, dict):
            raise OllamaError("Ollama returned an invalid response")
        return data

    def chat(self, system: str, user: str, json_schema: dict | None = None) -> str:
        body: dict = {
            "model": self.cfg.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_ctx": self.cfg.num_ctx, "temperature": 0},
        }
        if json_schema is not None:
            body["format"] = json_schema
        data = self._request("POST", "/api/chat", body)
        content = data.get("message", {}).get("content")
        if not isinstance(content, str):
            raise OllamaError("Ollama returned no message")
        return content

    def model_max_ctx(self) -> int:
        data = self._request("POST", "/api/show", {"model": self.cfg.model})
        info = data.get("model_info") or {}
        for key, value in info.items():
            if key.endswith(".context_length") and isinstance(value, int):
                return value
        raise OllamaError(f"cannot read the context length of model {self.cfg.model}")

    def list_models(self) -> list[str]:
        data = self._request("GET", "/api/tags")
        return [m["name"] for m in data.get("models", []) if "name" in m]

    def version(self) -> str:
        return str(self._request("GET", "/api/version").get("version", ""))
