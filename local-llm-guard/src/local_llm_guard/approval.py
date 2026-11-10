"""Ask the user, in a macOS dialog, to approve a change. Anything but a click on Write is a no."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

Approver = Callable[[str, str, bool], bool]  # (real diff, path, touches a secret line)

# `display dialog` does not scroll, so only a diff that surely fits on screen goes into it.
MAX_DIALOG_LINES = 60
MAX_DIALOG_CHARS = 4000
MAX_DIALOG_LINE_LEN = 200
SECRET_LINE_WARNING = "Warning: this change touches a line with a secret value."


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


def fits_dialog(diff: str) -> bool:
    lines = diff.splitlines()
    return (
        len(lines) <= MAX_DIALOG_LINES
        and len(diff) <= MAX_DIALOG_CHARS
        and all(len(line) <= MAX_DIALOG_LINE_LEN for line in lines)
    )


def ask_approval(diff: str, path: str, warning: bool = False, timeout_s: int = 120) -> bool:
    if sys.platform != "darwin":
        return False
    text = (SECRET_LINE_WARNING + "\n\n" if warning else "") + f"File: {path}\n\n"
    tmp: Path | None = None
    try:
        if fits_dialog(diff):
            text += diff
        else:
            d = _tmp_dir()
            d.mkdir(parents=True, exist_ok=True)
            os.chmod(d, 0o700)
            tmp = d / f"diff-{uuid.uuid4().hex}.diff"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(diff)
            opened = subprocess.run(
                ["open", "-e", str(tmp)], capture_output=True, timeout=30, check=False
            )
            if opened.returncode != 0:
                return False  # the user could not see the diff, so no dialog
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
