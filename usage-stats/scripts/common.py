#!/usr/bin/env python3
"""Shared paths, config and schema for the usage-stats plugin.

Every write path in this plugin resolves against STATE_DIR. Nothing is ever
written inside the plugin repository: the database holds excerpts of real
prompts and the weekly snapshots name real repositories and topics, and this
repository is public. Enforcing one base directory is the property; the
.gitignore entry is only a second layer under it.
"""
import json
import os
import sqlite3

STATE_DIR = os.path.expanduser(
    os.environ.get("CLAUDE_USAGE_STATS_HOME", "~/.claude/usage-stats")
)
DB_PATH = os.path.join(STATE_DIR, "stats.db")
CONFIG_PATH = os.path.join(STATE_DIR, "config.json")
WEEKLY_DIR = os.path.join(STATE_DIR, "weekly")
SCRATCH_DIR = os.path.join(STATE_DIR, "scratch")

TRANSCRIPT_ROOT = os.path.expanduser("~/.claude/projects")

# Gaps longer than this between two records mean the user was away. Those
# seconds are excluded from active_seconds but still counted in wall_seconds.
IDLE_GAP_SECONDS = 300

# Only the first this-many characters of a user prompt are stored. Assistant
# text, tool results and file contents are never stored at all.
PROMPT_HEAD_CHARS = 200

PROMPT_KINDS = (
    "task",
    "correction",
    "steer",
    "clarify_answer",
    "info_request",
    "meta",
)

DEFAULT_CONFIG = {
    "model": "claude-haiku-4-5-20251001",
    "batch_size": 10,
    "zero_output_token_threshold": 50000,
    # Ticket prefixes are organisation-specific, so they live here and never in
    # the published code. Example: ["PROJ", "OPS"].
    "ticket_prefixes": [],
    # Free-text hints that steer topic naming, e.g. ["billing", "infra"].
    "topic_hints": [],
}

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  transcript_path TEXT NOT NULL,
  transcript_mtime REAL NOT NULL,
  project_slug TEXT,
  cwd TEXT,
  repo TEXT,
  git_branch TEXT,
  session_kind TEXT,
  is_sidechain INTEGER DEFAULT 0,
  ai_title TEXT,
  started_at TEXT,
  ended_at TEXT,
  wall_seconds REAL,
  active_seconds REAL,
  n_user_prompts INTEGER DEFAULT 0,
  n_assistant INTEGER DEFAULT 0,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  tokens_cache_read INTEGER DEFAULT 0,
  tokens_cache_write INTEGER DEFAULT 0,
  models TEXT,
  n_tool_calls INTEGER DEFAULT 0,
  n_edit INTEGER DEFAULT 0,
  n_write INTEGER DEFAULT 0,
  n_bash INTEGER DEFAULT 0,
  n_commits INTEGER DEFAULT 0,
  n_claude_questions INTEGER DEFAULT 0,
  first_edit_turn INTEGER,
  indexed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_repo ON sessions(repo);

CREATE TABLE IF NOT EXISTS prompts (
  session_id TEXT NOT NULL,
  turn INTEGER NOT NULL,
  ts TEXT,
  chars INTEGER,
  text_head TEXT,
  kind TEXT,
  PRIMARY KEY (session_id, turn)
);
CREATE INDEX IF NOT EXISTS idx_prompts_kind ON prompts(kind);

CREATE TABLE IF NOT EXISTS classifications (
  session_id TEXT PRIMARY KEY,
  topic TEXT,
  model TEXT,
  classified_at TEXT,
  batch_tokens_in INTEGER,
  batch_tokens_out INTEGER
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT,
  finished_at TEXT,
  kind TEXT,
  files_scanned INTEGER,
  sessions_indexed INTEGER,
  sessions_classified INTEGER,
  calls INTEGER,
  cost_usd REAL,
  note TEXT
);
"""


def load_config():
    """Read the private config, filling in defaults for missing keys."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH) as fh:
            cfg.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return cfg


def assert_state_dir_outside_git():
    """Refuse to store data inside a git working tree.

    The database holds excerpts of real prompts and the snapshots name real
    repositories, so they must never become committable. Checking whether any
    parent directory contains a .git entry states the property. A list of
    ignored filenames in .gitignore would not: it protects the names it
    happens to mention and misses every file added later.
    """
    path = os.path.abspath(STATE_DIR)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            raise SystemExit(
                "refusing to run: %s lies inside the git repository at %s.\n"
                "Prompt excerpts must not be storable in version control.\n"
                "Set CLAUDE_USAGE_STATS_HOME to a directory outside any repository."
                % (STATE_DIR, path)
            )
        parent = os.path.dirname(path)
        if parent == path:
            return
        path = parent


def connect():
    """Open the database, creating the state directory and schema if needed."""
    assert_state_dir_outside_git()
    os.makedirs(STATE_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con
