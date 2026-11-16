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
    # "auto" marks text the user did not type. It is neither a correction nor
    # anything else the ratios describe, so it stays out of the denominator.
    classified = [r for r in prompt_rows if r["kind"] and r["kind"] != "auto"]
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


def _field(row, key):
    """Read a column from a sqlite3.Row or a dict; a missing key is None."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def is_measurable(session_row):
    """True when the external-write columns were filled for this session.

    NULL means the row was stored before those columns existed and its
    transcript was never read again, often because the file is gone. Such a
    session has an unknown result, which is different from no result.
    """
    return (
        _field(session_row, "n_external_write") is not None
        and _field(session_row, "n_subagent_produced") is not None
    )


def result_status(session_row, token_threshold):
    """Say whether a session produced something outside the chat.

    Returns one of:
      "cheap"      below the token threshold, not looked at
      "produced"   a file edit, commit, external write or subagent result
      "nothing"    measured, and none of those exists
      "unmeasured" no file edit or commit, and the other counters were never filled
    A file edit or commit settles the question even without the new counters.
    """
    if (_field(session_row, "tokens_out") or 0) <= token_threshold:
        return "cheap"
    own = (
        (_field(session_row, "n_edit") or 0)
        + (_field(session_row, "n_write") or 0)
        + (_field(session_row, "n_commits") or 0)
    )
    if own > 0:
        return "produced"
    if not is_measurable(session_row):
        return "unmeasured"
    # is_measurable() ruled out NULL above, so "or 0" only satisfies the type
    # checker and never hides an unmeasured value.
    others = (_field(session_row, "n_external_write") or 0) + (
        _field(session_row, "n_subagent_produced") or 0
    )
    return "produced" if others > 0 else "nothing"


def is_zero_output(session_row, token_threshold):
    """True when a session spent output tokens and measurably produced nothing.

    A session that is not measurable is not listed here. It has its own line in
    the report, so a missing transcript is never read as "nothing produced".
    """
    return result_status(session_row, token_threshold) == "nothing"


def is_unmeasured(session_row, token_threshold):
    """True when the result of a session above the threshold is unknown."""
    return result_status(session_row, token_threshold) == "unmeasured"


def is_background(session_row):
    """True for a background job, where elapsed time is machine time.

    A background job runs without the user watching, so its active time must
    not be added to the time the user personally spent.
    """
    return (session_row["session_kind"] or "interactive") == "bg"


def summarise_group(session_rows, prompt_rows, token_threshold):
    """Aggregate one group of sessions into the figures the report prints."""
    zero = [r for r in session_rows if is_zero_output(r, token_threshold)]
    unmeasured = [r for r in session_rows if is_unmeasured(r, token_threshold)]
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
        "unmeasured_sessions": len(unmeasured),
        "unmeasured_seconds": sum(r["active_seconds"] or 0 for r in unmeasured),
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
