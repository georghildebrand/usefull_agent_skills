#!/usr/bin/env python3
"""Pure functions that turn stored rows into the reported signals.

No database access and no I/O, so every function can be tested with plain
dictionaries. Rows may be sqlite3.Row objects or dicts.
"""
import statistics


def kind_ratio(prompt_rows, kind):
    """Share of classified prompts carrying `kind`.

    Prompts with no kind yet are excluded from the denominator, so a partly
    classified week reports the ratio of what is known instead of diluting it
    towards zero. Returns None when nothing is classified.
    """
    classified = [r for r in prompt_rows if r["kind"]]
    if not classified:
        return None
    return sum(1 for r in classified if r["kind"] == kind) / len(classified)


def median_first_edit_turn(session_rows):
    """Median number of prompts before the first file change.

    Sessions that never edited a file have no value to contribute and are
    excluded. They are reported separately as sessions without a result.
    """
    values = [
        r["first_edit_turn"] for r in session_rows if r["first_edit_turn"] is not None
    ]
    if not values:
        return None
    return statistics.median(values)


def is_zero_output(session_row, token_threshold):
    """True when a session spent output tokens but produced no lasting change.

    Needs all three: enough output tokens to matter, no file written, and no
    commit. A long discussion that ends in one edit is not counted.
    """
    if (session_row["tokens_out"] or 0) <= token_threshold:
        return False
    produced = (
        (session_row["n_edit"] or 0)
        + (session_row["n_write"] or 0)
        + (session_row["n_commits"] or 0)
    )
    return produced == 0


def is_background(session_row):
    """True for a background job, where elapsed time is machine time.

    A background job runs without the user watching, so its active time must
    not be added to the time the user personally spent.
    """
    return (session_row["session_kind"] or "interactive") == "bg"


def summarise_group(session_rows, prompt_rows, token_threshold):
    """Aggregate one group of sessions into the figures the report prints."""
    zero = [r for r in session_rows if is_zero_output(r, token_threshold)]
    return {
        "sessions": len(session_rows),
        "active_seconds": sum(r["active_seconds"] or 0 for r in session_rows),
        "active_interactive": sum(
            r["active_seconds"] or 0 for r in session_rows if not is_background(r)
        ),
        "active_background": sum(
            r["active_seconds"] or 0 for r in session_rows if is_background(r)
        ),
        "wall_seconds": sum(r["wall_seconds"] or 0 for r in session_rows),
        "tokens_out": sum(r["tokens_out"] or 0 for r in session_rows),
        "prompts": len(prompt_rows),
        "correction_ratio": kind_ratio(prompt_rows, "correction"),
        "steer_ratio": kind_ratio(prompt_rows, "steer"),
        "median_first_edit_turn": median_first_edit_turn(session_rows),
        "sessions_without_edit": sum(
            1 for r in session_rows if r["first_edit_turn"] is None
        ),
        "zero_output_sessions": len(zero),
        "zero_output_seconds": sum(r["active_seconds"] or 0 for r in zero),
    }


def fmt_duration(seconds):
    """Render seconds as 4h 12m, or 38m, or 45s."""
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%dh %02dm" % (h, m)
    if m:
        return "%dm" % m
    return "%ds" % s


def fmt_ratio(value):
    """Render a ratio as a percentage, or a dash when nothing is classified."""
    return "-" if value is None else "%d%%" % round(value * 100)


def fmt_tokens(n):
    """Render a token count compactly."""
    n = int(n or 0)
    if n >= 1_000_000:
        return "%.1fM" % (n / 1_000_000)
    if n >= 1_000:
        return "%dk" % (n // 1_000)
    return str(n)
