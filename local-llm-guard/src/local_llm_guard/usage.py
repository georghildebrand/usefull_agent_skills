"""Usage log: one JSON line per tool call, for later analysis.

Metadata only: tool, outcome, fixed error message, file paths and token counts, timings,
and how many values were masked. Never file content, questions, instructions, answers,
secret values or names. Writing the log never breaks a tool call.
"""

from __future__ import annotations

import json
import os
import re
import statistics
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

LOG_ENV = "LOCAL_LLM_GUARD_USAGE_LOG"  # a file path, or "off"
MAX_BYTES = 5_000_000  # then usage.jsonl moves to usage.jsonl.1 (one old file is kept)

_MASK_RE = re.compile(r"<(EMAIL|PHONE|IBAN|NAME|SECRET)(?:_\d+)?>")
_OUTCOMES = ("error", "approved", "rejected", "no change")
_front = "mcp"


def set_front(name: str) -> None:
    """Which front end runs: "mcp" (default) or "cli"."""
    global _front
    _front = name


def log_path(env: Mapping[str, str] = os.environ) -> Path | None:
    value = env.get(LOG_ENV, "").strip()
    if value.lower() == "off":
        return None
    if value:
        return Path(value).expanduser()
    return Path.home() / ".local" / "state" / "local-llm-guard" / "usage.jsonl"


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_masks(text: str) -> dict[str, int]:
    """Masks in a result text, by kind. <SECRET_n> and <SECRET> both count as secret."""
    return dict(Counter(m.lower() for m in _MASK_RE.findall(text)))


def outcome_of(text: str) -> str:
    for word in _OUTCOMES:
        if text.startswith(word + ":"):
            return word
    return "ok"


def _old(path: Path) -> Path:
    return path.with_name(path.name + ".1")


def record(entry: dict) -> None:
    path = log_path()
    if path is None:
        return
    row = {"ts": now_iso(), "front": _front, **entry}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        if path.exists() and path.stat().st_size >= MAX_BYTES:
            os.replace(path, _old(path))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError):
        pass  # a broken log must never break the tool call


def read_entries(path: Path, days: int | None = None) -> list[dict]:
    """Entries of the old and the current file, oldest first. Bad lines are skipped."""
    since = None
    if days is not None:
        since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    for p in (_old(path), path):
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and (since is None or str(row.get("ts", "")) >= since):
                rows.append(row)
    return rows


def summarize(rows: list[dict], path: str) -> str:
    if not rows:
        return f"usage log: {path}\nno entries"
    out = [
        f"usage log: {path}",
        f"{len(rows)} calls from {rows[0].get('ts')} to {rows[-1].get('ts')}",
    ]
    by_tool: dict[str, Counter] = {}
    for r in rows:
        by_tool.setdefault(str(r.get("tool")), Counter())[str(r.get("outcome"))] += 1
    out.append("calls by tool and outcome:")
    for tool, counts in sorted(by_tool.items()):
        parts = "  ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        out.append(f"  {tool:<7} {parts}")
    model_calls = [r for r in rows if r.get("tool") in ("ask", "task", "edit")]
    times = [r["duration_s"] for r in model_calls if isinstance(r.get("duration_s"), (int, float))]
    if times:
        out.append(
            f"duration of ask/task/edit: median {statistics.median(times):.1f} s, "
            f"max {max(times):.1f} s"
        )
    secrets = sum(r.get("secrets_masked") or 0 for r in model_calls)
    masks: Counter = Counter()
    for r in model_calls:
        masks.update(r.get("masks") or {})
    shown = ", ".join(f"{k} {v}" for k, v in sorted(masks.items())) or "none"
    out.append(f"secrets masked before the model: {secrets}; masks in results: {shown}")
    errors = Counter(str(r.get("error")) for r in rows if r.get("outcome") == "error")
    if errors:
        out.append("most common errors:")
        out += [f"  {n:>3}  {msg}" for msg, n in errors.most_common(5)]
    return "\n".join(out)
