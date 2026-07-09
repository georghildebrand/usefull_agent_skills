#!/usr/bin/env python3
"""Log a Tempo worklog against a Jira ticket.

Usage:
  tempo_log.py --issue PROJ-123 --date 2026-07-09 --hours 3.5 --desc "Review PR" [--dry-run]

Reads config/secrets from env (source your Atlassian env file first):
  JIRA_EMAIL           (your Jira account email)
  JIRA_SITE_URL         (e.g. https://your-site.atlassian.net)
  TEMPO_ACCOUNT_ID      (your Tempo/Jira accountId — find via issue assignee/reporter field)
  TEMPO_API_KEY         (Tempo Cloud API token, Bearer auth)
  ATLASSIAN_API_TOKEN   (Jira API token, Basic auth w/ JIRA_EMAIL)
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error


def jira_get(path, jira_site, email, token):
    req = urllib.request.Request(f"{jira_site}{path}")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def resolve_issue_id(issue_key, jira_site, email, jira_token):
    data = jira_get(f"/rest/api/3/issue/{issue_key}?fields=summary", jira_site, email, jira_token)
    return data["id"], data["fields"]["summary"]


def create_worklog(issue_id, date, hours, desc, account_id, tempo_token, dry_run):
    body = {
        "issueId": int(issue_id),
        "timeSpentSeconds": int(round(hours * 3600)),
        "startDate": date,
        "startTime": "09:00:00",
        "description": desc or ".",
        "authorAccountId": account_id,
    }
    if dry_run:
        print("DRY RUN — would POST:", json.dumps(body, indent=2))
        return

    req = urllib.request.Request(
        "https://api.tempo.io/4/worklogs",
        data=json.dumps(body).encode(),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {tempo_token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            print(json.load(resp))
    except urllib.error.HTTPError as e:
        print(f"FAILED {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True, help="Jira issue key, e.g. PROJ-123")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--hours", required=True, type=float)
    ap.add_argument("--desc", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jira_email = os.environ.get("JIRA_EMAIL")
    jira_site = os.environ.get("JIRA_SITE_URL")
    account_id = os.environ.get("TEMPO_ACCOUNT_ID")
    tempo_token = os.environ.get("TEMPO_API_KEY")
    jira_token = os.environ.get("ATLASSIAN_API_TOKEN")

    missing = [n for n, v in [
        ("JIRA_EMAIL", jira_email), ("JIRA_SITE_URL", jira_site),
        ("TEMPO_ACCOUNT_ID", account_id), ("TEMPO_API_KEY", tempo_token),
        ("ATLASSIAN_API_TOKEN", jira_token),
    ] if not v]
    if missing:
        print(f"Missing env vars: {', '.join(missing)} — source your Atlassian env file first", file=sys.stderr)
        sys.exit(1)

    issue_id, summary = resolve_issue_id(args.issue, jira_site, jira_email, jira_token)
    print(f"{args.issue} (id={issue_id}) — {summary}")
    create_worklog(issue_id, args.date, args.hours, args.desc, account_id, tempo_token, args.dry_run)


if __name__ == "__main__":
    main()
