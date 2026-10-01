#!/usr/bin/env python3
"""Read Claude Code transcripts and store one row per session and per prompt.

Reads ~/.claude/projects/*/*.jsonl. Never writes there. Only the first
PROMPT_HEAD_CHARS characters of each user prompt are stored; assistant text,
tool results and file contents are not stored at all.

Usage:
  extract.py                 index transcripts changed since the last run
  extract.py --since 8w      index transcripts changed in the last 8 weeks
  extract.py --all           index every transcript
  extract.py --file PATH     index one transcript (used by the tests)
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    IDLE_GAP_SECONDS,
    PROMPT_HEAD_CHARS,
    TRANSCRIPT_ROOT,
    connect,
)

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
# The harness injects context into user records inside this tag. It is a single
# fixed protocol tag, not a category, so matching it by name has no hole.
REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
DURATION_RE = re.compile(r"^(\d+)([dwh])$")


def parse_since(spec):
    """Turn '8w', '30d' or '12h' into a unix timestamp, or None."""
    if not spec:
        return None
    m = DURATION_RE.match(spec.strip())
    if not m:
        raise SystemExit("--since expects a form like 8w, 30d or 12h")
    n, unit = int(m.group(1)), m.group(2)
    seconds = {"h": 3600, "d": 86400, "w": 604800}[unit] * n
    return datetime.now(timezone.utc).timestamp() - seconds


def ts_of(rec):
    """Parse a record timestamp into a unix timestamp, or None."""
    raw = rec.get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def user_text(rec):
    """Return the human-written text of a user record, or None.

    Skips meta records, tool results, and records whose only content was
    harness-injected context.
    """
    if rec.get("isMeta") or rec.get("toolUseResult") is not None:
        return None
    content = rec.get("message", {}).get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_result":
                return None
    else:
        return None
    text = REMINDER_RE.sub("", "\n".join(parts)).strip()
    return text or None


def repo_of(cwd):
    """Name the git repository containing cwd.

    Walks up looking for a .git entry rather than matching known path shapes:
    a worktree stores .git as a file, and a path pattern list would miss
    layouts it does not name.
    """
    if not cwd:
        return None
    path = cwd
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return os.path.basename(path) or None
        parent = os.path.dirname(path)
        if parent == path:
            return os.path.basename(cwd) or None
        path = parent


def iter_records(path):
    """Yield each parsable JSON object from a transcript, streaming the file.

    Transcripts reach hundreds of megabytes, so the file is never read whole.
    A line that does not parse is skipped: a session still being written can
    end in a partial line.
    """
    with open(path, errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def extract_file(path):
    """Aggregate one transcript file into {session_id: {row, prompts, ...}}."""
    sessions = {}
    for rec in iter_records(path):
        sid = rec.get("sessionId") or rec.get("session_id")
        if not sid:
            continue
        st = sessions.setdefault(
            sid,
            {
                "row": {
                    "session_id": sid,
                    "transcript_path": path,
                    "transcript_mtime": os.path.getmtime(path),
                    "project_slug": os.path.basename(os.path.dirname(path)),
                    "cwd": None,
                    "repo": None,
                    "git_branch": None,
                    "session_kind": "interactive",
                    "is_sidechain": 0,
                    "ai_title": None,
                    "n_user_prompts": 0,
                    "n_assistant": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "tokens_cache_read": 0,
                    "tokens_cache_write": 0,
                    "n_tool_calls": 0,
                    "n_edit": 0,
                    "n_write": 0,
                    "n_bash": 0,
                    "n_commits": 0,
                    "n_claude_questions": 0,
                    "first_edit_turn": None,
                },
                "prompts": [],
                "models": set(),
                "times": [],
            },
        )
        row = st["row"]

        if rec.get("type") == "ai-title" and rec.get("aiTitle"):
            row["ai_title"] = rec["aiTitle"]
            continue

        if rec.get("cwd") and not row["cwd"]:
            row["cwd"] = rec["cwd"]
        if rec.get("gitBranch") and not row["git_branch"]:
            row["git_branch"] = rec["gitBranch"]
        if rec.get("sessionKind"):
            row["session_kind"] = rec["sessionKind"]
        if rec.get("isSidechain"):
            row["is_sidechain"] = 1

        t = ts_of(rec)
        if t is not None:
            st["times"].append(t)

        if rec.get("type") == "user":
            text = user_text(rec)
            if text:
                row["n_user_prompts"] += 1
                st["prompts"].append(
                    {
                        "turn": row["n_user_prompts"],
                        "ts": rec.get("timestamp"),
                        "chars": len(text),
                        "text_head": text[:PROMPT_HEAD_CHARS],
                    }
                )

        elif rec.get("type") == "assistant":
            row["n_assistant"] += 1
            msg = rec.get("message", {}) or {}
            if msg.get("model"):
                st["models"].add(msg["model"])
            usage = msg.get("usage") or {}
            row["tokens_in"] += usage.get("input_tokens") or 0
            row["tokens_out"] += usage.get("output_tokens") or 0
            row["tokens_cache_read"] += usage.get("cache_read_input_tokens") or 0
            row["tokens_cache_write"] += usage.get("cache_creation_input_tokens") or 0
            for block in msg.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                row["n_tool_calls"] += 1
                if name in EDIT_TOOLS:
                    row["n_edit"] += 1
                    if name == "Write":
                        row["n_write"] += 1
                    if row["first_edit_turn"] is None:
                        row["first_edit_turn"] = max(1, row["n_user_prompts"])
                elif name == "Bash":
                    row["n_bash"] += 1
                    cmd = (block.get("input") or {}).get("command") or ""
                    if "git commit" in cmd:
                        row["n_commits"] += 1
                elif name == "AskUserQuestion":
                    row["n_claude_questions"] += 1

    for st in sessions.values():
        row, times = st["row"], sorted(st["times"])
        row["models"] = ",".join(sorted(st["models"])) or None
        if times:
            row["started_at"] = datetime.fromtimestamp(
                times[0], timezone.utc
            ).isoformat()
            row["ended_at"] = datetime.fromtimestamp(times[-1], timezone.utc).isoformat()
            row["wall_seconds"] = times[-1] - times[0]
            row["active_seconds"] = sum(
                b - a for a, b in zip(times, times[1:]) if b - a <= IDLE_GAP_SECONDS
            )
        else:
            row["started_at"] = row["ended_at"] = None
            row["wall_seconds"] = row["active_seconds"] = 0.0
        row["repo"] = repo_of(row["cwd"])
        row["indexed_at"] = datetime.now(timezone.utc).isoformat()
    return sessions


def store(con, sessions):
    """Insert or replace sessions and their prompts. Returns rows written.

    A session that already exists is only replaced when the new record carries
    at least as many assistant messages. Forked transcripts can share a session
    id, and a short fork must not overwrite the full session.
    """
    written = 0
    for sid, st in sessions.items():
        row = st["row"]
        prev = con.execute(
            "SELECT n_assistant FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        if prev and prev["n_assistant"] > row["n_assistant"]:
            continue
        cols = sorted(row)
        con.execute(
            "INSERT OR REPLACE INTO sessions (%s) VALUES (%s)"
            % (",".join(cols), ",".join("?" * len(cols))),
            [row[c] for c in cols],
        )
        # Keep any kind already assigned to a prompt so re-extracting a growing
        # transcript does not throw away classification work.
        old = {
            r["turn"]: r["kind"]
            for r in con.execute(
                "SELECT turn, kind FROM prompts WHERE session_id = ?", (sid,)
            )
        }
        con.execute("DELETE FROM prompts WHERE session_id = ?", (sid,))
        con.executemany(
            "INSERT INTO prompts (session_id,turn,ts,chars,text_head,kind)"
            " VALUES (?,?,?,?,?,?)",
            [
                (sid, p["turn"], p["ts"], p["chars"], p["text_head"], old.get(p["turn"]))
                for p in st["prompts"]
            ],
        )
        written += 1
    con.commit()
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", help="only files changed in this window, e.g. 8w")
    ap.add_argument("--all", action="store_true", help="index every transcript")
    ap.add_argument("--file", help="index a single transcript file")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    con = connect()
    started = datetime.now(timezone.utc).isoformat()

    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(os.path.join(TRANSCRIPT_ROOT, "*", "*.jsonl")))
        if not args.all:
            cutoff = parse_since(args.since)
            if cutoff is None:
                last = con.execute(
                    "SELECT MAX(transcript_mtime) AS m FROM sessions"
                ).fetchone()["m"]
                cutoff = last or 0
            files = [f for f in files if os.path.getmtime(f) >= cutoff]

    indexed = 0
    for path in files:
        try:
            indexed += store(con, extract_file(path))
        except OSError as exc:
            print("skipped %s: %s" % (path, exc), file=sys.stderr)

    con.execute(
        "INSERT INTO runs (started_at,finished_at,kind,files_scanned,sessions_indexed)"
        " VALUES (?,?,?,?,?)",
        (
            started,
            datetime.now(timezone.utc).isoformat(),
            "extract",
            len(files),
            indexed,
        ),
    )
    con.commit()
    if not args.quiet:
        print("scanned %d transcripts, indexed %d sessions" % (len(files), indexed))


if __name__ == "__main__":
    main()
