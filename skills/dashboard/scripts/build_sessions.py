#!/usr/bin/env python3
"""Build the sessions tile document from Claude Code session files.

Usage: build_sessions.py <out.json>

Reads ~/.claude/sessions/<pid>.json and ~/.claude/projects/*/<sessionId>.jsonl.
Unknown fields are ignored. Missing fields become "" and never crash.
"""
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def _iso(epoch_seconds):
    dt = datetime.datetime.fromtimestamp(epoch_seconds, datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ms(value):
    """Epoch milliseconds as seconds, or None when missing or not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value / 1000.0


def _transcript_mtime(projects_dir, session_id):
    if not session_id:
        return None
    pattern = os.path.join(glob.escape(projects_dir), "*", glob.escape(session_id) + ".jsonl")
    times = []
    for path in glob.glob(pattern):
        try:
            times.append(os.path.getmtime(path))
        except OSError:
            continue
    return max(times) if times else None


def _short_cwd(cwd, home):
    if not isinstance(cwd, str):
        return ""
    if home and (cwd == home or cwd.startswith(home.rstrip("/") + "/")):
        return "~" + cwd[len(home.rstrip("/")):]
    return cwd


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def build(sessions_dir, projects_dir, home):
    items = []
    newest = None
    for path in sorted(glob.glob(os.path.join(glob.escape(sessions_dir), "*.json"))):
        s = _load(path)
        if s is None:
            continue
        sid = s.get("sessionId") if isinstance(s.get("sessionId"), str) else ""
        transcript = _transcript_mtime(projects_dir, sid)
        started = _ms(s.get("startedAt"))
        times = [t for t in (transcript, _ms(s.get("statusUpdatedAt")), _ms(s.get("updatedAt")), started) if t is not None]
        last = max(times) if times else None
        if last is not None:
            newest = last if newest is None else max(newest, last)
        name = s.get("name") if isinstance(s.get("name"), str) and s.get("name") else sid[:8]
        items.append({
            "name": name,
            "kind": s.get("kind") if isinstance(s.get("kind"), str) else "",
            "state": s.get("status") if isinstance(s.get("status"), str) else "",
            "startedAt": _iso(started) if started is not None else "",
            "lastActiveAt": _iso(last) if last is not None else "",
            "cwd": _short_cwd(s.get("cwd"), home),
            "hasTranscript": transcript is not None,
        })
    items.sort(key=lambda i: i["lastActiveAt"], reverse=True)
    return common.fit_document(common.envelope(
        "sessions", items, updatedAt=_iso(newest) if newest is not None else ""))


def main(argv):
    if len(argv) != 2:
        sys.exit("usage: build_sessions.py <out.json>")
    home = os.path.expanduser("~")
    doc = build(os.path.join(home, ".claude", "sessions"),
                os.path.join(home, ".claude", "projects"), home)
    common.write_json(argv[1], doc)


if __name__ == "__main__":
    main(sys.argv)
