"""Merge new newsfeed items into the stored feed and track sync markers."""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

FMT = "%Y-%m-%dT%H:%M:%SZ"


def _parse(ts):
    return datetime.datetime.strptime(ts, FMT).replace(tzinfo=datetime.timezone.utc)


def _fmt(dt):
    return dt.strftime(FMT)


def merge(existing, new_items, now, keep_days=30):
    """Return a feed document: new items first, no duplicate ids, old items dropped."""
    cutoff = _fmt(_parse(now) - datetime.timedelta(days=keep_days))
    old_items = (existing or {}).get("items", [])
    seen = set()
    items = []
    for item in list(new_items) + list(old_items):
        if item["id"] in seen or item["changedAt"] < cutoff:
            continue
        seen.add(item["id"])
        items.append(item)
    doc = common.envelope("feed", items)
    doc["syncedAt"] = now
    return doc


def markers(existing_markers, source, now):
    """Return markers with `source` set to now. Other sources are kept."""
    return {**(existing_markers or {}), source: now}


def since(markers_, source, now):
    """Stored marker for source, or now minus 7 days."""
    stored = (markers_ or {}).get(source)
    if stored:
        return stored
    return _fmt(_parse(now) - datetime.timedelta(days=7))
