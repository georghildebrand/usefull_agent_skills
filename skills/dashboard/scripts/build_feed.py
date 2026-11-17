"""Merge new newsfeed items into the stored feed and track sync markers.

Markers are stored as ISO 8601 UTC with Z. JQL and CQL do not take that form:
query_time() turns a marker into the "yyyy-MM-dd HH:mm" form they take.
"""
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
    return common.fit_document(doc)


def markers(existing_markers, source, now):
    """Return markers with `source` set to now. Other sources are kept."""
    return {**(existing_markers or {}), source: now}


def since(markers_, source, now):
    """Stored marker for source, or now minus 7 days."""
    stored = (markers_ or {}).get(source)
    if stored:
        return stored
    return _fmt(_parse(now) - datetime.timedelta(days=7))


def item_id(source, native_id, changed_at):
    """Feed item id "<source>:<native id>:<changedAt>".

    The change time is part of the id. A page or ticket that changes again gets
    a new id, so a read mark (feed/read, keyed by id) does not hide the new change.
    """
    return "%s:%s:%s" % (source, native_id, changed_at)


# JQL and CQL read a date in the time zone of the user's profile. With no known
# zone, going back 14 hours covers every zone (UTC-12 to UTC+14). merge() removes
# the items that come back twice.
NO_ZONE_MARGIN = datetime.timedelta(hours=14)


def query_time(marker, tz=None, margin_minutes=5):
    """Marker as "yyyy-MM-dd HH:mm" for a JQL or CQL date comparison.

    tz is the IANA zone name of the user's profile (Jira /rest/api/3/myself
    field timeZone, for example "Europe/Berlin"). The time is moved back by
    margin_minutes, because the query form has no seconds. Without tz, or with
    a zone this Python does not know, the UTC time minus 14 hours is returned.
    """
    dt = _parse(marker) - datetime.timedelta(minutes=margin_minutes)
    zone = None
    if tz:
        try:
            import zoneinfo
            zone = zoneinfo.ZoneInfo(tz)
        except (ImportError, ValueError, OSError, KeyError):
            zone = None
    if zone is None:
        return (dt - NO_ZONE_MARGIN).strftime("%Y-%m-%d %H:%M")
    return dt.astimezone(zone).strftime("%Y-%m-%d %H:%M")
