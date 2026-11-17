"""Shared helpers for building dashboard tile documents (JSON)."""
import datetime
import json

LIMIT = 262144


def now_iso():
    """Current UTC time as ISO 8601 with a trailing Z."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def envelope(source, items, **extra):
    """Wrap items in the common document envelope."""
    return {"v": 1, "syncedAt": now_iso(), "source": source, "items": items, **extra}


def _size(doc):
    return len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))


def fit_document(doc, limit=LIMIT):
    """Drop items from the end until the JSON is under limit bytes.

    Sets `truncated` to the number of dropped items when any were dropped.
    The first item is always kept.
    """
    items = list(doc.get("items", []))
    total = len(items)
    kept = total
    out = dict(doc, items=items)
    while _size(out) >= limit and kept > 1:
        # Halve the excess first for speed, then step by one near the limit.
        kept = max(1, kept - max(1, (kept - 1) // 8))
        out = dict(doc, items=items[:kept], truncated=total - kept)
    return out


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False)
        fh.write("\n")
