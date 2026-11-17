# Tile: feed

Documents: `feed/items`, `feed/markers`. The page writes `feed/read` (`{<item id>: true}`). This recipe never writes `feed/read`.

## Source

Read-only. From the preset it needs `sources.confluence` (space keys), `sources.jira` (project keys) and the CLI profile.
Read `feed/markers` first (`{confluence: <time>, jira: <time>}`) and `feed/items` (existing).
`now` is the current UTC time as `2026-11-17T09:00:00Z`.
`build_feed.since(markers, source, now)` returns the stored marker, or now minus 7 days on a first run.
The marker stays in ISO form (`2026-11-17T09:00:00Z`). JQL and CQL do not accept that form,
and they read a date in the time zone of the user's profile. So `<since>` in the queries
below is always `build_feed.query_time(marker, tz)`, for example `2026-11-17 09:55`.
`tz` is the field `timeZone` of `atlassian-cli --profile <profile> jira api /rest/api/3/myself`
(for example `Europe/Berlin`); use it for both Jira and Confluence. Without it, pass `None`:
query_time then goes back 14 hours, which covers every time zone. query_time also goes back
5 minutes, because the query form has no seconds. Items that come back twice have the same
id, and `merge()` removes them.

Confluence, two queries (changed in the spaces, and mentions of the user):

```
atlassian-cli --profile <profile> confluence api /wiki/rest/api/search \
  --query 'cql=space in (<spaces>) and lastmodified >= "<since>"' --query limit=50 --output <scratchpad>/cf-changed.json --force
atlassian-cli --profile <profile> confluence api /wiki/rest/api/search \
  --query 'cql=mention = currentUser() and lastmodified >= "<since>"' --query limit=50 --output <scratchpad>/cf-mention.json --force
```

Jira, two queries (changed in the projects, and watched by the user):

```
atlassian-cli --profile <profile> jira api /rest/api/3/search/jql \
  --query 'jql=project in (<keys>) and updated >= "<since>"' --query maxResults=50 \
  --query 'fields=summary,updated' --output <scratchpad>/jira-changed.json --force
atlassian-cli --profile <profile> jira api /rest/api/3/search/jql \
  --query 'jql=watcher = currentUser() and updated >= "<since>"' --query maxResults=50 \
  --query 'fields=summary,updated' --output <scratchpad>/jira-watching.json --force
```

## Build

Map each result to an item with a short Python snippet (`sys.path.insert(0, '<skill dir>/scripts')`):
`{id: build_feed.item_id(source, <page id or ticket key>, changedAt), title, link, source: "confluence" or "jira", why: "changed" | "mention" | "watching", changedAt: <ISO UTC, Z>}`.
The id is `"<source>:<native id>:<changedAt>"`, for example `jira:<key>:2026-11-17T08:00:00Z`.
The change time is part of the id on purpose: `feed/read` is keyed by id, so when a page or
ticket the user has read changes again, the new change gets a new id and shows as new.
Links are absolute `https` links. A mention wins over "changed" when an item is in both results.

Then merge with `build_feed.merge(existing, new_items, now)`. It puts new items first, removes duplicate ids and drops items older than 30 days. Write the result to `feed/items` with `ArtifactData` `set` and `if_version`.
Only after both writes succeed, call `build_feed.markers(old_markers, source, now)` for each source that was fetched and write `feed/markers`. A failed fetch keeps the old marker.
The session never writes `feed/read`. It may drop ids of items older than 30 days from it.

## Left out

Page bodies, comment text, author names, attachments.
