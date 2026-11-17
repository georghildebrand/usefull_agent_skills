#!/usr/bin/env python3
"""Build the Jira tile document from a /rest/api/3/search/jql issue list.

Fetching stays in the tile recipe. This module only maps issues to items.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def _get(obj, *path):
    """Walk nested dicts; return "" when any step is missing or null."""
    for key in path:
        if not isinstance(obj, dict):
            return ""
        obj = obj.get(key)
    return obj if isinstance(obj, str) else ("" if obj is None else obj)


def _iso(value):
    """Jira date (2026-11-17T09:12:00.000+0000) as ISO UTC with Z; "" if unparsable."""
    if not isinstance(value, str) or not value:
        return ""
    text = value.replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
        return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ""


def _role(fields, my_id):
    if my_id and _get(fields, "assignee", "accountId") == my_id:
        return "assignee"
    if my_id and _get(fields, "reporter", "accountId") == my_id:
        return "reporter"
    return "other"


def browse_url(site):
    """Ticket link base "<site>/browse/". The page appends the key to it.

    site is the Jira site address ("https://site.example.net" or with a trailing
    "/"). A value that already ends with "/browse" or "/browse/" is kept.
    """
    if not isinstance(site, str) or not site:
        return ""
    site = site.rstrip("/")
    if site.endswith("/browse"):
        return site + "/"
    return site + "/browse/"


def build(issues, my_account_id, base_url, scope=""):
    """Map issues to the jira/open document. base_url is the site address."""
    items = []
    for order, issue in enumerate(issues):
        if not isinstance(issue, dict):
            continue
        f = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        items.append({
            "key": _get(issue, "key"),
            "title": _get(f, "summary"),
            "project": _get(f, "project", "key"),
            "type": _get(f, "issuetype", "name"),
            "status": _get(f, "status", "name"),
            "statusCat": _get(f, "status", "statusCategory", "key"),
            "priority": _get(f, "priority", "name"),
            "updatedAt": _iso(_get(f, "updated")),
            "createdAt": _iso(_get(f, "created")),
            "role": _role(f, my_account_id),
            "parent": _get(f, "parent", "key"),
            "order": order,
        })
    return common.fit_document(common.envelope("jira", items, baseUrl=browse_url(base_url), scope=scope))
