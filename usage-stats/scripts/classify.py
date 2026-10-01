#!/usr/bin/env python3
"""Assign a topic to each session and a kind to each prompt, using one model.

Sessions are classified in batches. A single `claude -p` call carries a fixed
floor of roughly 19,000 input tokens, because Claude Code always ships its base
system prompt; measured on 2026-09-08, switching off tools, MCP servers and
setting sources moved 38,700 tokens to 18,900 and did not remove the floor.
Batching spreads that fixed cost over many sessions instead of paying it once
per session.

Usage:
  classify.py --dry-run          show planned calls and estimated cost
  classify.py                    classify every session that has no topic yet
  classify.py --limit 20         classify at most 20 sessions
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    PROMPT_KINDS,
    SCRATCH_DIR,
    connect,
    load_config,
)

# Both constants are measured, not guessed: 6 batches of 10 sessions on
# 2026-09-08 averaged 9,458 input and 14,095 output tokens per call.
#
# Input carries a fixed floor because Claude Code always ships a base system
# prompt, so the per-call cost barely depends on prompt length. That is the
# reason for batching.
HARNESS_INPUT_FLOOR = 9500
# Output per session, including thinking tokens. Thinking dominates: output is
# five times the input price and about 1,400 tokens per session are produced
# regardless of how few prompts that session holds. An earlier estimate
# counted only the visible JSON and came out three times too low.
OUTPUT_TOKENS_PER_SESSION = 1400
# List prices per million tokens for the default model. On a subscription no
# per-token charge appears and the calls consume usage limits instead; both
# are printed.
PRICE_IN_PER_M = 1.0
PRICE_OUT_PER_M = 5.0

MAX_PROMPTS_PER_SESSION = 40

FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")

INSTRUCTION = """You label Claude Code sessions for a personal time report.

For each session below, return:
- "topic": 2-4 words, kebab-case, naming the subject of work. Reuse the same
  wording across sessions that share a subject so they group together.
- "kinds": one label per prompt turn, choosing exactly one of:
  task            a new request for work
  correction      rejects or fixes what the assistant just did
  steer           changes direction or scope during the task
  clarify_answer  answers a question the assistant asked
  info_request    a question only, no change wanted
  meta            about the assistant, its tools, or permissions

Judge "correction" by whether the prompt rejects or redirects the previous
answer, not by whether it contains particular words.

Return ONLY a JSON array, one object per session, no prose and no code fence:
[{"n": 1, "topic": "...", "kinds": {"1": "task", "2": "correction"}}]
"""


EMPTY_TOPIC = "(no prompts)"


def mark_empty_sessions(con):
    """Give sessions that hold no human prompt a topic without calling a model.

    Aborted and immediately closed sessions have nothing to classify. Sending
    them costs tokens and returns an empty topic, so they are settled locally.
    """
    now = datetime.now(timezone.utc).isoformat()
    rows = con.execute(
        """SELECT s.session_id
             FROM sessions s
             LEFT JOIN classifications c USING (session_id)
            WHERE c.session_id IS NULL AND s.n_user_prompts = 0"""
    ).fetchall()
    con.executemany(
        "INSERT OR REPLACE INTO classifications"
        " (session_id,topic,model,classified_at,batch_tokens_in,batch_tokens_out)"
        " VALUES (?,?,?,?,0,0)",
        [(r["session_id"], EMPTY_TOPIC, "none", now) for r in rows],
    )
    con.commit()
    return len(rows)


def fetch_pending(con, limit):
    """Sessions with prompts but no topic yet, oldest first.

    Oldest first on purpose: each batch is shown the topics already assigned,
    so the vocabulary grows as work proceeds. Newest first would classify the
    most recent week against an empty vocabulary, which is the week most
    likely to be reported.
    """
    return con.execute(
        """SELECT s.session_id, s.repo, s.ai_title
             FROM sessions s
             LEFT JOIN classifications c USING (session_id)
            WHERE c.session_id IS NULL AND s.n_user_prompts > 0
            ORDER BY s.started_at ASC
            LIMIT ?""",
        (limit,),
    ).fetchall()


def reset(con):
    """Drop every assigned topic and prompt kind so they are recomputed.

    Needed after changing topic_hints or the instruction: topics are cached
    per session and would otherwise never be revisited.
    """
    n = con.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
    con.execute("DELETE FROM classifications")
    con.execute("UPDATE prompts SET kind = NULL")
    con.commit()
    return n


def prompts_of(con, session_id):
    return con.execute(
        "SELECT turn, text_head FROM prompts WHERE session_id = ?"
        " ORDER BY turn LIMIT ?",
        (session_id, MAX_PROMPTS_PER_SESSION),
    ).fetchall()


# High enough that the list is not the limit in practice. An earlier cap of 40
# reintroduced the fragmentation it was meant to prevent: once more than 40
# topics existed, the least used ones dropped out of the list and were invented
# again under new names, which is exactly the long tail that needs the list
# most. 200 topics cost roughly 2,000 extra input tokens per call, about a
# fifth of a cent.
MAX_KNOWN_TOPICS = 200


def known_topics(con, limit=MAX_KNOWN_TOPICS):
    """Topics already assigned, most used first.

    Each batch is a separate call and cannot see what earlier batches chose.
    Without this list the same subject gets a new name in every batch, so the
    report ends up with "systemgraph-development" and "system-graph-testing"
    as separate rows and no group large enough to be informative.
    """
    return [
        r["topic"]
        for r in con.execute(
            """SELECT topic, COUNT(*) n FROM classifications
                WHERE topic IS NOT NULL AND topic != ?
                GROUP BY topic ORDER BY n DESC, topic LIMIT ?""",
            (EMPTY_TOPIC, limit),
        )
    ]


def build_prompt(con, batch, topic_hints):
    """Render one batch as text. Sessions are numbered, not named by id.

    Numbering keeps the reply small and removes any chance of the model
    mistyping a session id.
    """
    parts = [INSTRUCTION]
    existing = known_topics(con)
    if existing:
        parts.append(
            "Topics already in use. Reuse one exactly when the subject matches,"
            " instead of inventing a near-duplicate:\n%s\n" % ", ".join(existing)
        )
    if topic_hints:
        parts.append("Prefer these topic names where they fit: %s\n" % ", ".join(topic_hints))
    for n, row in enumerate(batch, 1):
        parts.append("--- session %d" % n)
        if row["repo"]:
            parts.append("repo: %s" % row["repo"])
        if row["ai_title"]:
            parts.append("title: %s" % row["ai_title"])
        lines = prompts_of(con, row["session_id"])
        if not lines:
            parts.append("prompts: (none)")
        else:
            parts.append("prompts:")
            for p in lines:
                parts.append("%d: %s" % (p["turn"], (p["text_head"] or "").replace("\n", " ")))
    return "\n".join(parts)


def call_model(prompt, model):
    """Run one classification call and return (text, cost_usd, usage).

    Runs from an empty scratch directory on purpose: Claude Code discovers
    CLAUDE.md by walking up from the working directory, and --setting-sources
    does not suppress that. Without the empty directory a user's project
    instructions would be sent on every call.
    """
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    proc = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--model",
            model,
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--allowed-tools",
            "",
            "--no-session-persistence",
            "--system-prompt",
            "Return only the requested JSON. No prose.",
            "--output-format",
            "json",
        ],
        cwd=SCRATCH_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        # Keep the tail, not the head. A wrapper around the claude binary can
        # print a banner first, and the head of stderr then shows only that
        # banner while the real error sits at the end.
        raise RuntimeError(
            "claude exited %d: %s" % (proc.returncode, proc.stderr.strip()[-800:])
        )
    payload = json.loads(proc.stdout)
    # --output-format json returns either a result object or a list of events,
    # depending on the flags in use. Accept both rather than depending on one.
    if isinstance(payload, list):
        payload = next(
            (e for e in payload if isinstance(e, dict) and e.get("type") == "result"),
            {},
        )
    return payload.get("result", ""), payload.get("total_cost_usd") or 0.0, payload.get("usage") or {}


def parse_reply(text, size):
    """Parse the model reply into a list of per-session objects."""
    cleaned = FENCE_RE.sub("", text.strip())
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("no JSON array in reply")
    data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("reply is not a JSON array")
    by_n = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("n"))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= size:
            by_n[n] = item
    if not by_n:
        raise ValueError("no usable session objects in reply")
    return by_n


def apply_batch(con, batch, by_n, model, cost_in, cost_out):
    """Write topics and prompt kinds for one batch."""
    now = datetime.now(timezone.utc).isoformat()
    applied = 0
    for n, row in enumerate(batch, 1):
        item = by_n.get(n)
        if not item:
            continue
        topic = (item.get("topic") or "").strip().lower() or None
        con.execute(
            "INSERT OR REPLACE INTO classifications"
            " (session_id,topic,model,classified_at,batch_tokens_in,batch_tokens_out)"
            " VALUES (?,?,?,?,?,?)",
            (row["session_id"], topic, model, now, cost_in, cost_out),
        )
        kinds = item.get("kinds") or {}
        if isinstance(kinds, dict):
            for turn, kind in kinds.items():
                if kind not in PROMPT_KINDS:
                    continue
                try:
                    turn_i = int(turn)
                except (TypeError, ValueError):
                    continue
                con.execute(
                    "UPDATE prompts SET kind = ? WHERE session_id = ? AND turn = ?",
                    (kind, row["session_id"], turn_i),
                )
        applied += 1
    con.commit()
    return applied


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="estimate only, call nothing")
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--batch-size", type=int)
    ap.add_argument(
        "--reset",
        action="store_true",
        help="drop all topics and prompt kinds, then classify again",
    )
    args = ap.parse_args()

    cfg = load_config()
    model = cfg["model"]
    batch_size = args.batch_size or cfg["batch_size"]

    con = connect()
    if args.reset:
        print("dropped %d cached classifications" % reset(con))
    empty = mark_empty_sessions(con)
    if empty:
        print("%d sessions hold no prompt and were settled without a call" % empty)
    pending = fetch_pending(con, args.limit)
    if not pending:
        print("nothing to classify")
        return

    batches = list(chunks(pending, batch_size))
    if args.dry_run:
        n_prompts = sum(
            len(prompts_of(con, r["session_id"])) for r in pending
        )
        est_in = len(batches) * HARNESS_INPUT_FLOOR + n_prompts * 60
        est_out = len(pending) * OUTPUT_TOKENS_PER_SESSION
        usd = est_in / 1e6 * PRICE_IN_PER_M + est_out / 1e6 * PRICE_OUT_PER_M
        print(
            "%d sessions, %d prompts, batch size %d -> %d calls"
            % (len(pending), n_prompts, batch_size, len(batches))
        )
        print(
            "estimated %s input and %s output tokens, list price about USD %.2f"
            % (f"{est_in:,}", f"{est_out:,}", usd)
        )
        print(
            "output includes thinking tokens and drives most of the cost;"
            " on a Claude subscription no per-token charge applies and the"
            " calls consume usage limits instead"
        )
        return

    started = datetime.now(timezone.utc).isoformat()
    total_cost, calls, applied, failures = 0.0, 0, 0, []
    for i, batch in enumerate(batches, 1):
        remaining = [batch]
        while remaining:
            current = remaining.pop(0)
            prompt = build_prompt(con, current, cfg.get("topic_hints") or [])
            try:
                text, cost, usage = call_model(prompt, model)
                calls += 1
                total_cost += cost
                by_n = parse_reply(text, len(current))
            except (RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
                if len(current) > 1:
                    half = max(1, len(current) // 2)
                    remaining[:0] = [current[:half], current[half:]]
                    continue
                failures.append("%s: %s" % (current[0]["session_id"][:8], exc))
                continue
            applied += apply_batch(
                con,
                current,
                by_n,
                model,
                usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0),
                usage.get("output_tokens", 0),
            )
        print(
            "batch %d/%d done, %d sessions classified, USD %.3f so far"
            % (i, len(batches), applied, total_cost),
            flush=True,
        )

    con.execute(
        "INSERT INTO runs (started_at,finished_at,kind,sessions_classified,calls,cost_usd,note)"
        " VALUES (?,?,?,?,?,?,?)",
        (
            started,
            datetime.now(timezone.utc).isoformat(),
            "classify",
            applied,
            calls,
            total_cost,
            "; ".join(failures[:10]) or None,
        ),
    )
    con.commit()
    print(
        "classified %d of %d sessions in %d calls, list price USD %.2f"
        % (applied, len(pending), calls, total_cost)
    )
    if failures:
        print("%d sessions could not be classified" % len(failures), file=sys.stderr)


if __name__ == "__main__":
    main()
