#!/usr/bin/env python3
"""Print a weekly usage report as a terminal table.

Wall-clock time per session is stored but never reported: a resumed session
spans days between its first and last record, which made the summed figure
meaningless. Active time counts only gaps shorter than IDLE_GAP_SECONDS.

Usage:
  report.py                       previous completed ISO week
  report.py --week 2026-W36       one specific week
  report.py --weeks 4             the last 4 completed weeks, compared
  report.py --write-snapshot      also write the week to a Markdown file
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import WEEKLY_DIR, connect, load_config  # noqa: E402
from signals import (  # noqa: E402
    fmt_duration,
    fmt_ratio,
    fmt_tokens,
    summarise_group,
)

TOPIC_COL = 30


def week_bounds(iso_week):
    """Return (start, end_exclusive) as UTC datetimes for an ISO week string."""
    year, week = iso_week.split("-W")
    monday = date.fromisocalendar(int(year), int(week), 1)
    start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=7)


def previous_weeks(n):
    """The n most recent completed ISO weeks, oldest first."""
    today = datetime.now(timezone.utc).date()
    last_monday = today - timedelta(days=today.weekday())
    weeks = []
    for i in range(n, 0, -1):
        monday = last_monday - timedelta(weeks=i)
        y, w, _ = monday.isocalendar()
        weeks.append("%d-W%02d" % (y, w))
    return weeks


def load_week(con, iso_week):
    """Sessions and prompts of one week, grouped by topic."""
    start, end = week_bounds(iso_week)
    sessions = con.execute(
        """SELECT s.*, COALESCE(c.topic, '(unclassified)') AS topic
             FROM sessions s
             LEFT JOIN classifications c USING (session_id)
            WHERE s.started_at >= ? AND s.started_at < ?
              AND s.n_user_prompts > 0""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    ids = [r["session_id"] for r in sessions]
    prompts = []
    if ids:
        prompts = con.execute(
            "SELECT * FROM prompts WHERE session_id IN (%s)"
            % ",".join("?" * len(ids)),
            ids,
        ).fetchall()
    return sessions, prompts


def group_by_topic(sessions, prompts, threshold):
    by_session = {}
    for p in prompts:
        by_session.setdefault(p["session_id"], []).append(p)
    groups = {}
    for s in sessions:
        groups.setdefault(s["topic"], {"sessions": [], "prompts": []})
        groups[s["topic"]]["sessions"].append(s)
        groups[s["topic"]]["prompts"].extend(by_session.get(s["session_id"], []))
    return {
        topic: summarise_group(g["sessions"], g["prompts"], threshold)
        for topic, g in groups.items()
    }


def render_week(con, iso_week, threshold):
    """Return the report for one week as a list of text lines."""
    sessions, prompts = load_week(con, iso_week)
    start, end = week_bounds(iso_week)
    out = []
    out.append(
        "Week %s  (%s to %s)"
        % (iso_week, start.date(), (end - timedelta(days=1)).date())
    )
    if not sessions:
        out.append("  no sessions with prompts in this week")
        return out

    classified = sum(1 for s in sessions if s["topic"] != "(unclassified)")
    kinded = sum(1 for p in prompts if p["kind"])
    out.append(
        "Basis: %d sessions, %d with a topic; %d of %d prompts labelled"
        % (len(sessions), classified, kinded, len(prompts))
    )
    if prompts and kinded < 0.8 * len(prompts):
        # Both causes for a missing label sit late in a session: the cap on
        # prompts per session, and the model omitting turns near the end of a
        # long list. Late prompts are the ones more likely to be corrections,
        # so Corr and Steer below are floors, not measurements.
        out.append(
            "        only %d%% labelled, and the unlabelled ones sit late in"
            " long sessions," % round(100.0 * kinded / len(prompts))
        )
        out.append(
            "        so Corr and Steer are lower bounds rather than measurements"
        )
    interactive = sum(1 for s in sessions if s["session_kind"] != "bg")
    out.append(
        "        %d interactive, %d background jobs"
        % (interactive, len(sessions) - interactive)
    )
    out.append("")

    groups = group_by_topic(sessions, prompts, threshold)
    # Sort by the user's own time, which is the question the report answers.
    order = sorted(groups.items(), key=lambda kv: -kv[1]["active_interactive"])

    fmt = "%-*s %5s %9s %9s %8s %7s %7s %6s"
    header = fmt % (
        TOPIC_COL, "Topic", "Sess", "You", "Backgrd", "Out-tok", "Corr", "Steer", "->Edit",
    )
    out.append(header)
    out.append("-" * len(header))

    def line(label, g):
        return fmt % (
            TOPIC_COL,
            label[:TOPIC_COL],
            g["sessions"],
            fmt_duration(g["active_interactive"]),
            fmt_duration(g["active_background"]),
            fmt_tokens(g["tokens_out"]),
            fmt_ratio(g["correction_ratio"]),
            fmt_ratio(g["steer_ratio"]),
            "-" if g["median_first_edit_turn"] is None
            else "%g" % g["median_first_edit_turn"],
        )

    for topic, g in order:
        out.append(line(topic, g))
    total = summarise_group(sessions, prompts, threshold)
    out.append("-" * len(header))
    out.append(line("TOTAL", total))
    out.append("")
    out.append("You = active time in interactive sessions, the time you spent. This")
    out.append("        is a lower bound: a pause longer than 5 minutes is dropped,")
    out.append("        so reading a long answer before replying is not counted.")
    out.append("Backgrd = active time of background jobs, which ran without you")
    out.append("        watching. The two are never added together.")
    out.append("Corr = share of prompts that reject or fix the previous answer.")
    out.append("Steer = share that change direction mid-task; high means the goal")
    out.append("        was unclear at the start, which needs a different fix.")
    out.append("->Edit = median number of prompts before the first file change.")
    out.append("")

    out.append("WHERE EFFORT PRODUCED NOTHING")
    zero = [
        s for s in sessions
        if (s["tokens_out"] or 0) > threshold
        and (s["n_edit"] or 0) + (s["n_write"] or 0) + (s["n_commits"] or 0) == 0
    ]
    if not zero:
        out.append("  none: every session above the token threshold changed something")
    else:
        out.append(
            "  %d sessions spent over %s output tokens with no edit and no commit,"
            % (len(zero), fmt_tokens(threshold))
        )
        out.append(
            "  %s of active time in total."
            % fmt_duration(sum(s["active_seconds"] or 0 for s in zero))
        )
        for s in sorted(zero, key=lambda r: -(r["active_seconds"] or 0))[:8]:
            out.append(
                "    %8s  %3d prompts  %-24s %s"
                % (
                    fmt_duration(s["active_seconds"]),
                    s["n_user_prompts"],
                    s["topic"][:24],
                    (s["ai_title"] or "(no title)")[:40],
                )
            )
    out.append("")

    out.append("PROMPT KINDS")
    counts = {}
    for p in prompts:
        if p["kind"]:
            counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    if not counts:
        out.append("  no prompts labelled yet; run classify.py")
    else:
        n = sum(counts.values())
        out.append(
            "  "
            + "   ".join(
                "%s %d%%" % (k, round(v / n * 100))
                for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
            )
        )
        out.append("  (%d labelled prompts)" % n)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week", help="ISO week, e.g. 2026-W36")
    ap.add_argument("--weeks", type=int, help="compare the last N completed weeks")
    ap.add_argument("--write-snapshot", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    threshold = cfg["zero_output_token_threshold"]
    con = connect()

    weeks = [args.week] if args.week else previous_weeks(args.weeks or 1)
    for i, wk in enumerate(weeks):
        if i:
            print("\n" + "=" * 72 + "\n")
        lines = render_week(con, wk, threshold)
        print("\n".join(lines))
        if args.write_snapshot:
            os.makedirs(WEEKLY_DIR, exist_ok=True)
            path = os.path.join(WEEKLY_DIR, "%s.md" % wk)
            with open(path, "w") as fh:
                fh.write("# Claude Code usage, week %s\n\n```\n" % wk)
                fh.write("\n".join(lines))
                fh.write("\n```\n")
            print("\nsnapshot written to %s" % path)


if __name__ == "__main__":
    main()
