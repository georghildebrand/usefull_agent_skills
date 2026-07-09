---
name: tempo-worklog-cli
description: >
  Use when logging or querying Tempo Timesheets worklogs on Jira Cloud (Tempo
  app inside Jira), or when the user wants to fill in hours, check logged
  time, or automate Tempo timesheet entries via API instead of the browser
  week view.
---

# Tempo Worklog CLI

Tempo Timesheets is a Jira Cloud marketplace app — separate REST API
(`api.tempo.io/4`), separate Bearer token, NOT covered by `atlassian-cli`
(see companion skill `atlassian-cli-usage` for Jira/Confluence/Bitbucket).

## When to Use

- Fill/check Tempo hours without opening browser week view
- Bulk-log worklogs across days/tickets
- Query logged hours for a date range

## Setup (one-time)

1. In Jira: Apps → Tempo → gear icon (bottom-left) → **API Integration** → **New Token**
2. Add to your Atlassian env file:
   ```
   export JIRA_EMAIL=you@example.com
   export JIRA_SITE_URL=https://your-site.atlassian.net
   export TEMPO_ACCOUNT_ID=...      # find via issue assignee/reporter field or profile URL
   export ATLASSIAN_API_TOKEN=...   # Jira REST, Basic auth
   export TEMPO_API_KEY=...         # Tempo REST, Bearer auth
   ```
3. Never read env files with credentials directly — `source` them.

## Auth model — two different schemes

| API | Base | Auth |
|---|---|---|
| Jira REST v3 | `<JIRA_SITE>.atlassian.net/rest/api/3` | Basic (`email:ATLASSIAN_API_TOKEN`, base64) |
| Tempo REST v4 | `api.tempo.io/4` | Bearer `TEMPO_API_KEY` |

Tempo worklogs reference issues by **numeric Jira `issueId`**, not the issue
key (`<PROJECT>-<NUM>`). Resolve key → id first via Jira REST
(`GET /rest/api/3/issue/{key}?fields=summary`), or POSTs fail/reject silently
wrong ticket.

## Query worklogs (scope to yourself!)

`GET /4/worklogs?from=&to=` returns **whole org's** worklogs, not just yours.
Scope with `/4/worklogs/user/{accountId}`:

```bash
source <path-to-your-atlassian-env-file>
curl -s -H "Authorization: Bearer $TEMPO_API_KEY" \
  "https://api.tempo.io/4/worklogs/user/<ACCOUNT_ID>?from=<FROM_DATE>&to=<TO_DATE>"
```

Find your `accountId` once via `atlassian-cli jira issue get <any-key> -f json`
(assignee/reporter field) or Jira profile page URL, then reuse.

## Create a worklog

`tempo_log.py` (bundled alongside this SKILL.md) resolves issue key → id via
Jira REST, builds worklog payload, POSTs to Tempo with Bearer auth. Copy it
anywhere on your machine, or run in place.

```bash
source <path-to-your-atlassian-env-file>
python3 tempo_log.py \
  --issue <PROJECT>-<NUM> --date <YYYY-MM-DD> --hours <N> --desc "<summary>" \
  [--dry-run]
```

`--dry-run` prints payload without sending.

## Common Mistakes

- Using `atlassian-cli` for Tempo — no support, wrong tool
- Passing issue **key** instead of numeric **id** to Tempo POST — rejected
- Querying `/4/worklogs` without `/user/{accountId}` — returns org-wide data, not yours
- Mixing auth schemes — Jira=Basic, Tempo=Bearer, different tokens entirely
