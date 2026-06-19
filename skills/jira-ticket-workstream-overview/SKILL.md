---
name: jira-ticket-workstream-overview
description: >
  Use when someone wants an overview of their Jira tickets (created by them
  and/or assigned to them) cross-referenced against their current workstreams
  pulled from an agent memory system — producing a status snapshot, what's
  coming up, and blind spots. Triggers: "ticket overview", "where are we",
  "my tickets vs workstreams".
---

# Jira Ticket ↔ Workstream Overview

Live overview of person's Jira tickets matched to current workstreams from
agent memory system. Output = status snapshot + upcoming work + blind spots.
Always live — re-run every invocation, never reuse stale snapshot.

## When To Use

User asks "where are we", "overview of my tickets", "match my tickets to our
workstreams", or similar.

## Prerequisites

- `atlassian-cli` configured with at least one Jira profile (see
  `atlassian-cli-setup` and `atlassian-cli-usage` skills).
- Agent memory system exposing project-overview / project-summary tool (see
  `agent-memory-hygiene`). Skill uses generic verbs — *bootstrap*, *project
  overview*, *refresh summary*, *supersede a note* — map to whatever memory
  tooling available.

## Steps

### 1. Auth check

```bash
atlassian-cli auth list
atlassian-cli auth test
```

If user works across more than one Atlassian org, each org = separate profile
with own token. Profile with expired token (`Invalid or expired credentials`)
hides every ticket in that org — call out in output, suggest
`atlassian-cli auth login --profile <PROFILE>`. Don't block on it; report
against profiles that authenticate.

### 2. Pull tickets — two lenses

Run both. `reporter` = tickets user authored (backlog-author / architect view);
`assignee` = tickets they actively own. **Gap between the two**
(reported-but-unassigned) = blind-spot signal, not noise.

```bash
echo "=== reported by me ==="
atlassian-cli --profile <JIRA_PROFILE> jira issue search \
  --jql "reporter = currentUser() ORDER BY updated DESC" --limit 100
echo "=== assigned to me ==="
atlassian-cli --profile <JIRA_PROFILE> jira issue search \
  --jql "assignee = currentUser() ORDER BY updated DESC" --limit 100
```

Large result sets may exceed inline size, persist to file — read that file
rather than re-running with smaller limit and losing tickets.

### 3. Pull live workstreams from memory

Bootstrap memory system's routing rules first, then request project overview
for relevant project. Overview should yield: project summary note,
concept/workstream list, recent activity timeline.

Use **recent timeline** to judge which workstreams hot vs cold — high
recent-session count signals active focus even when matching Jira tickets still
sit in backlog.

Default to user's primary project if they don't name one.

### 4. Match tickets → workstreams

Cluster every ticket under a workstream. Derive clusters **fresh** each run from
memory concepts + ticket epic links + summary keywords — don't hardcode
workstream list, goes stale. Per cluster, cite backing memory item(s) so
mapping traceable.

### 5. Output

Terse, table-driven:

1. **Active now** — In Progress / In Review / To Do, table: key | status | what | workstream.
2. **Paused** — cold-but-owned tickets.
3. **Workstreams** — each cluster with its tickets + backing memory item(s); flag hot vs cold.
4. **Blind spots** ⚠️ — cross-check Jira state against memory:
   - Ticket status lagging reality (memory says resolved, ticket still open).
   - Reported-but-unassigned children under owned parent (filed ≠ staffed).
   - Workstreams hot in memory but stuck in backlog on board (analysis not converted to tracked execution).
   - Stream paused on one side while sibling stream moves (split-brain / coordination gap).
   - External dependencies with no ETA tracked.
   - Expired auth hiding an org.
5. **Coming up** — next logical moves.

### 6. Compare against the project summary, offer update

Project overview returns current **project summary** note. Diff findings
against what summary claims:

- Workstream now active in tickets but absent/stale in summary.
- Summary status live tickets contradict.
- New workstream with no concept yet.

If drift exists, **surface as short list, offer to update** — never write
silently. Typical write paths in memory system:

- *refresh the project summary* — regenerates from recent history; often does
  **not** promote new items into curated "key concepts" section.
- *supersede the summary note* — explicit path to edit key concepts or fix
  stated status.

Only write on explicit go-ahead.

End by offering to drill into one workstream, pull full descriptions/comments
for active tickets, draft close-outs / sub-task assignments, or apply summary
update.

## Notes

- Read-only by default. Never transition or assign tickets without explicit ask.
- This is a *skill*, not a *script*: value (workstream matching, blind-spot
  reasoning, summary-drift diff) needs a model. Plain shell script could only
  dump the two JQL tables.
- Companions: `atlassian-cli-usage` (CLI gotchas — harmless 204 parse error,
  profile selection, ADF), `agent-memory-hygiene` (memory item quality).
