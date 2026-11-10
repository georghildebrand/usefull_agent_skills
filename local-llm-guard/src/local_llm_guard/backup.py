"""Backups of files before an edit. Private directory, pruned by age."""

from __future__ import annotations

import os
import time
from pathlib import Path


def default_root() -> Path:
    return Path.home() / ".local" / "state" / "local-llm-guard" / "backups"


def backup_file(path: Path, root: Path | None = None, data: bytes | None = None) -> Path:
    """Copy the file bytes to <root>/<path with / as %>.<YYYYmmdd-HHMMSS>."""
    root = root or default_root()
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    if data is None:
        data = Path(path).read_bytes()
    base = str(path).replace("/", "%") + "." + time.strftime("%Y%m%d-%H%M%S")
    n = 0
    while True:
        target = root / (base if n == 0 else f"{base}-{n}")
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            n += 1
            continue
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        return target


def prune_backups(days: int = 30, root: Path | None = None) -> int:
    """Delete backups older than `days`. Returns the number removed."""
    root = root or default_root()
    if not root.is_dir():
        return 0
    cutoff = time.time() - days * 86400
    removed = 0
    for f in root.iterdir():
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed
