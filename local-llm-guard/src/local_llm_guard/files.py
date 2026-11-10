"""Load small text files for the model. Refuses anything unsafe before reading."""

from __future__ import annotations

import math
import re
import string
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


_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def estimate_tokens(text: str) -> int:
    """Upper estimate of the prompt tokens, so that a file is never cut without an error.

    1 token each: digits, ASCII punctuation and symbols, and every letter of a word that
    holds a digit (hex, base64, ids). A non-ASCII character counts its UTF-8 bytes, the most
    a byte-level tokenizer can use. Other letters and spaces: 1 token per 3 characters.
    """
    one = 0
    for ch in text:
        if ord(ch) > 127:
            one += len(ch.encode("utf-8", errors="surrogatepass"))
        elif ch.isdigit() or ch in string.punctuation:
            one += 1
    loose = sum(1 for ch in text if ord(ch) < 128 and (ch.isalpha() or ch.isspace()))
    for word in _WORD_RE.findall(text):
        if any(ch.isdigit() for ch in word):
            letters = sum(1 for ch in word if ch.isalpha())
            one += letters
            loose -= letters
    return one + math.ceil(loose / 3)


_SPACE_RUN_RE = re.compile(r"[ \t]{2,}")
_NON_ASCII_RE = re.compile(r"[^\x00-\x7f]")


def typical_tokens(text: str) -> int:
    """A closer guess than estimate_tokens, used only to spot a prompt that Ollama cut.

    Same rules, but a non-ASCII character and a run of spaces or tabs count 1 token each.
    """
    return estimate_tokens(_NON_ASCII_RE.sub("!", _SPACE_RUN_RE.sub("!", text)))


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
