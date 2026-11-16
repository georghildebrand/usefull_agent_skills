"""Thin MCP layer. All logic lives in service.py."""

from __future__ import annotations

import os
from collections.abc import Callable

from mcp.server.mcpserver import MCPServer

from local_llm_guard import service
from local_llm_guard.backup import prune_backups
from local_llm_guard.config import Config, config_from_env
from local_llm_guard.ollama import Client, OllamaClient


def build_server(
    holder: dict[str, Config], client_factory: Callable[[Config], Client] = OllamaClient
) -> MCPServer:
    """holder["cfg"] is the one live Config; local_config replaces it in memory only."""
    auto = os.environ.get("LOCAL_LLM_GUARD_AUTO") == "1"
    # WARNING level: the SDK must not log tool arguments or results.
    mcp = MCPServer(
        "local-llm-guard",
        instructions=service.instructions_text(auto, os.environ.get("SENSITIVE_CANARY_SKIP_TOOLS")),
        log_level="WARNING",
    )

    def client() -> Client:
        return client_factory(holder["cfg"])

    @mcp.tool()
    def local_ask(paths: list[str], question: str) -> str:
        """Ask a question about files with a local model; returns a filtered answer.

        Use only for small text files that Claude may not read directly.
        Paths must be absolute. At most 5 files.
        """
        try:
            return service.ask(paths, question, client(), holder["cfg"])
        except Exception as exc:  # noqa: BLE001
            return service.error_text(exc)

    @mcp.tool()
    def local_task(paths: list[str], instruction: str) -> str:
        """Run an instruction on files with a local model; returns a filtered answer.

        Use only for small text files that Claude may not read directly.
        Paths must be absolute. At most 5 files.
        """
        try:
            return service.task(paths, instruction, client(), holder["cfg"])
        except Exception as exc:  # noqa: BLE001
            return service.error_text(exc)

    @mcp.tool()
    def local_edit(path: str, instruction: str) -> str:
        """Edit one text file with a local model after the user approves the diff.

        The user sees the real diff in a dialog and must click Write. Path must be absolute.
        Returns approved or rejected plus a filtered diff.
        """
        try:
            return service.edit(path, instruction, client(), holder["cfg"])
        except Exception as exc:  # noqa: BLE001
            return service.error_text(exc)

    @mcp.tool()
    def local_status() -> str:
        """Show the local model, context size and Ollama status."""
        try:
            return service.status(client(), holder["cfg"])
        except Exception as exc:  # noqa: BLE001
            return service.error_text(exc)

    @mcp.tool()
    def local_config(
        num_ctx: int | None = None, model: str | None = None, timeout_s: int | None = None
    ) -> str:
        """Change num_ctx, model or timeout_s until restart. Ask the user first."""
        try:
            cfg, message = service.configure(
                client(), holder["cfg"], num_ctx=num_ctx, model=model, timeout_s=timeout_s
            )
        except Exception as exc:  # noqa: BLE001
            return service.error_text(exc)
        holder["cfg"] = cfg
        return message

    return mcp


def main() -> None:
    try:
        prune_backups()
    except OSError:
        pass  # an unreadable backup folder must not stop the server; the next start tries again
    build_server({"cfg": config_from_env(os.environ)}).run("stdio")


if __name__ == "__main__":
    main()
