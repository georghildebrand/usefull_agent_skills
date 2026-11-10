"""Load small text files for the model. Refuses anything unsafe before reading."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

MAX_FILES = 5
ANSWER_RESERVE = 1024


class FileRefused(Exception):
    """A file or a set of files must not be sent to the model."""


@dataclass
class LoadedFile:
    path: Path
    text: str
    tokens: int


def estimate_tokens(text: str) -> int:
    """Upper estimate: models give each digit its own token; other text needs at most 1 per 3."""
    digits = sum(ch.isdigit() for ch in text)
    return digits + math.ceil((len(text) - digits) / 3)


def _is_env_name(name: str) -> bool:
    return ".env" in name.lower()


def load_files(paths: list[str]) -> list[LoadedFile]:
    if len(paths) > MAX_FILES:
        raise FileRefused(f"too many files: {len(paths)} given, the limit is {MAX_FILES}")
    resolved: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            raise FileRefused(f"{raw}: only absolute paths are accepted")
        if _is_env_name(p.name):
            raise FileRefused(".env files are never read")
        try:
            real = p.resolve(strict=True)
        except (FileNotFoundError, NotADirectoryError):
            raise FileRefused(f"{raw}: file not found") from None
        except (OSError, RuntimeError):
            raise FileRefused(f"{raw}: cannot resolve path") from None
        if _is_env_name(real.name):
            raise FileRefused(".env files are never read")
        if real.is_dir():
            raise FileRefused(f"{real}: is a directory")
        resolved.append(real)
    loaded: list[LoadedFile] = []
    for real in resolved:
        try:
            data = real.read_bytes()
        except PermissionError:
            raise FileRefused(f"cannot read {real}: denied, check the sandbox profile") from None
        except OSError:
            raise FileRefused(f"cannot read {real}") from None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise FileRefused(f"{real}: not a text file") from None
        if "\x00" in text:
            raise FileRefused(f"{real}: not a text file")
        loaded.append(LoadedFile(path=real, text=text, tokens=estimate_tokens(text)))
    return loaded


def check_budget(files: list[LoadedFile], prompt: str, num_ctx: int) -> None:
    """`prompt` is the exact text sent: system prompt, file headers, file text and task."""
    total = estimate_tokens(prompt) + ANSWER_RESERVE
    if total > num_ctx:
        listing = ", ".join(f"{f.path} ({f.tokens} tokens)" for f in files)
        raise FileRefused(
            f"input too large: {listing}; about {total} tokens needed with answer reserve, "
            f"limit is {num_ctx}; raise it with local_config"
        )
