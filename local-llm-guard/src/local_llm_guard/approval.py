"""Ask the user, in a macOS dialog, to approve a change. Anything but a click on Write is a no."""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

Approver = Callable[[str, str], bool]

MAX_DIALOG_LINES = 60


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _tmp_dir() -> Path:
    return Path.home() / ".local" / "state" / "local-llm-guard" / "tmp"


def build_script(text: str, name: str, timeout_s: int) -> str:
    title = _esc(f"local-llm-guard: change to {name}")
    return (
        f'display dialog "{_esc(text)}" with title "{title}" '
        f'buttons {{"Cancel", "Write"}} default button "Cancel" '
        f"giving up after {int(timeout_s)}"
    )


def ask_approval(diff: str, path: str, timeout_s: int = 120) -> bool:
    text = f"File: {path}\n\n"
    tmp: Path | None = None
    try:
        if len(diff.splitlines()) <= MAX_DIALOG_LINES:
            text += diff
        else:
            d = _tmp_dir()
            d.mkdir(parents=True, exist_ok=True)
            os.chmod(d, 0o700)
            tmp = d / f"diff-{uuid.uuid4().hex}.diff"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(diff)
            subprocess.run(["open", "-e", str(tmp)], capture_output=True, timeout=30, check=False)
            text += "The diff is long. The full diff is open in TextEdit."
        script = build_script(text, Path(path).name, timeout_s)
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout_s + 30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass
    out = proc.stdout or ""
    return proc.returncode == 0 and "button returned:Write" in out and "gave up:true" not in out
