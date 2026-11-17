# Tile: feed

Documents: `feed/items`, `feed/markers`. The page writes `feed/read` (`{<item id>: true}`). This recipe never writes `feed/read`.

## Source

Read-only. From the preset it needs `sources.confluence` (space keys), `sources.jira` (project keys) and the CLI profile.
Read `feed/markers` first (`{confluence: <time>, jira: <time>}`) and `feed/items` (existing).
`now` is the current UTC time as `2026-11-17T09:00:00Z`.
`build_feed.since(markers, source, now)` returns the stored marker, or now minus 7 days on a first run.

Confluence, two queries (changed in the spaces, and mentions of the user):

```
atlassian-cli --profile <profile> confluence api /wiki/rest/api/search \
  --query 'cql=space in (<spaces>) and lastmodified >= "<since>"' --query limit=50 --output <scratchpad>/cf-changed.json
atlassian-cli --profile <profile> confluence api /wiki/rest/api/search \
  --query 'cql=mention = currentUser() and lastmodified >= "<since>"' --query limit=50 --output <scratchpad>/cf-mention.json
```

Jira, two queries (changed in the projects, and watched by the user):

```
atlassian-cli --profile <profile> jira api /rest/api/3/search/jql \
  --query 'jql=project in (<keys>) and updated >= "<since>"' --query maxResults=50 \
  --query 'fields=summary,updated' --output <scratchpad>/jira-changed.json
atlassian-cli --profile <profile> jira api /rest/api/3/search/jql \
  --query 'jql=watcher = currentUser() and updated >= "<since>"' --query maxResults=50 \
  --query 'fields=summary,updated' --output <scratchpad>/jira-watching.json
```

## Build

Map each result to an item with a short Python snippet:
`{id: "confluence:<id>" or "jira:<key>", title, link, source: "confluence" or "jira", why: "changed" | "mention" | "watching", changedAt: <ISO UTC, Z>}`.
Links are absolute `https` links. A mention wins over "changed" when an item is in both results.

Then merge with `build_feed.merge(existing, new_items, now)`. It puts new items first, removes duplicate ids and drops items older than 30 days. Write the result to `feed/items` with `ArtifactData` `set` and `if_version`.
Only after both writes succeed, call `build_feed.markers(old_markers, source, now)` for each source that was fetched and write `feed/markers`. A failed fetch keeps the old marker.
The session never writes `feed/read`. It may drop ids of items older than 30 days from it.

## Left out

Page bodies, comment text, author names, attachments.
