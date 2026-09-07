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

## First-time use — learn the user's pattern

Before logging anything, if the user's usual work pattern isn't already
known (default hours, default ticket/account for plain dev work, leave/
vacation ticket + pattern), ask for it — a screenshot of an existing Tempo
time-record entry is the fastest way for the user to convey exact
field values (ticket, duration, account, description convention).

Once learned, offer to persist it as a personal default so it doesn't need
re-asking each session — in the user's own `CLAUDE.md` (project or global),
**not** in this skill file. Work patterns, ticket keys, and account codes are
org-specific/private and must stay out of shared skill repos — see
`skill-confidentiality-boundary`.

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
  --issue <PROJECT>-<NUM> --date <YYYY-MM-DD> --start <HH:MM> --end <HH:MM> \
  --desc "<summary>" --account <ACCOUNT_KEY> \
  [--dry-run]
```

`--dry-run` prints payload without sending. `--account` is optional — omit if
your Tempo instance doesn't use the Account work-attribute.

### Setting the "Account" field

If your org's Tempo UI shows an **Account** dropdown on time records, that's a
Tempo work-attribute (key `_Account_`), not a native worklog field. Look up
valid account keys via:

```bash
curl -s -H "Authorization: Bearer $TEMPO_API_KEY" "https://api.tempo.io/4/accounts" \
  | python3 -c "import json,sys; [print(a['key'],'|',a['name']) for a in json.load(sys.stdin)['results']]"
```

**Gotcha:** the create-worklog POST wants `attributes` as a **bare array**:
`[{"key": "_Account_", "value": "<ACCOUNT_KEY>"}]`. Wrapping it as
`{"values": [...]}` (the shape Tempo returns on GET) fails with a Jackson
deserialization error (`Cannot deserialize value of type HashSet<...>`).

## Example: workday + vacation pattern

Once learned (see "First-time use" above), a typical personal pattern looks
like this — store the real values in the user's own CLAUDE.md, not here:

```
Default workday: 08:30–12:00 and 13:00–18:00 (two entries, split by lunch)
Default dev-work ticket: <DEV_TICKET_KEY> (e.g. "Dev Work" bucket ticket)
Default account: <ACCOUNT_KEY>
Description: ticket number if relevant, else "."

Vacation/leave ticket: <LEAVE_TICKET_KEY> (e.g. "Leaves" bucket ticket)
Vacation entry: single 9h block, 09:00–18:00, same account, desc "."
```

Bulk-logging vacation over a date range: enumerate weekdays only (skip
Sat/Sun) and confirm the exact date list with the user before firing writes
— these are real timesheet records, not trivially reversible.

## Common Mistakes

- Using `atlassian-cli` for Tempo — no support, wrong tool
- Passing issue **key** instead of numeric **id** to Tempo POST — rejected
- Querying `/4/worklogs` without `/user/{accountId}` — returns org-wide data, not yours
- Mixing auth schemes — Jira=Basic, Tempo=Bearer, different tokens entirely
- Wrapping `attributes` in `{"values": [...]}` on POST — bare array only
