"""Command-line front end. Runs the same service functions as the MCP tools."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable

from local_llm_guard import server, service, usage
from local_llm_guard.backup import prune_backups
from local_llm_guard.config import Config, config_from_env
from local_llm_guard.ollama import Client, OllamaClient


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        raise _UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="local-llm-guard")
    sub = p.add_subparsers(dest="command")
    ask = sub.add_parser("ask", help="ask a question about files")
    ask.add_argument("paths", nargs="+")
    ask.add_argument("-q", "--question", required=True)
    task = sub.add_parser("task", help="run an instruction on files")
    task.add_argument("paths", nargs="+")
    task.add_argument("-i", "--instruction", required=True)
    edit = sub.add_parser("edit", help="edit one file after approval in a dialog")
    edit.add_argument("path")
    edit.add_argument("-i", "--instruction", required=True)
    sub.add_parser("status", help="show model and Ollama status")
    sub.add_parser("serve", help="start the MCP server on stdio")
    use = sub.add_parser("usage", help="summarise the usage log (metadata only)")
    use.add_argument("--days", type=int, default=None, help="only the last N days")
    return p


def _dispatch(args: argparse.Namespace, client: Client, cfg: Config) -> str:
    if args.command == "ask":
        return service.ask(args.paths, args.question, client, cfg)
    if args.command == "task":
        return service.task(args.paths, args.instruction, client, cfg)
    if args.command == "edit":
        return service.edit(args.path, args.instruction, client, cfg)
    return service.status(client, cfg)


def main(
    argv: list[str] | None = None,
    client_factory: Callable[[Config], Client] = OllamaClient,
) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        args = build_parser().parse_args(argv)
        if args.command in (None, "serve"):
            server.main()
            return 0
        if args.command == "usage":
            path = usage.log_path()
            if path is None:
                print(f"usage log is off ({usage.LOG_ENV}=off)")
                return 0
            print(usage.summarize(usage.read_entries(path, args.days), str(path)))
            return 0
        usage.set_front("cli")
        if args.command == "edit":
            try:
                prune_backups()
            except OSError:
                pass  # an unreadable backup folder must not stop an edit
        cfg = config_from_env(os.environ)
        result = _dispatch(args, client_factory(cfg), cfg)
    except _UsageError as exc:
        result = f"error: usage: {exc}"
    except SystemExit:
        result = "error: usage: local-llm-guard [ask|task|edit|status|usage|serve] ..."
    except Exception as exc:  # noqa: BLE001 - fail closed, nothing on stderr
        result = service.error_text(exc)
    print(result)
    return 1 if result.startswith("error:") else 0


def run() -> None:
    sys.exit(main())
