# Benchmark: atlassian-cli vs Rovo MCP

Date: 2026-08-28. Same Jira Cloud site, same account, same operations:
create epic → create story A → create story B (same epic) → create
sub-task (linked to story B) → JQL search (children of epic) → status
transition (story A → In Progress).

## Results

| Step | atlassian-cli | Rovo MCP |
|---|---|---|
| Create epic | 1.77s | 8.99s |
| Create story A | 1.03s | 8.48s |
| Create story B | 1.18s | 8.40s |
| Create sub-task (linked) | 1.75s | 8.65s |
| JQL search (children of epic) | 0.54s | 6.76s |
| Status transition | 1.51s | 11.59s (2 calls: `getTransitionsForJiraIssue` + `transitionJiraIssue`) |
| **Total** | **7.78s** | **52.88s** |

**atlassian-cli ~7x faster** for identical Jira CRUD + search + transition
sequence.

## Why

- CLI: one subprocess, one network call per operation. Status transition
  resolves the transition name to an ID server-side in a single request.
- Rovo MCP: separate protocol round-trip per tool call, and some operations
  need two calls where the CLI needs one (transition lookup before apply).
- Rovo MCP response payloads are ~4x larger per issue (full avatar URLs,
  `self` links, `expand` metadata) — more tokens spent per call, not just
  more wall-clock time.

## Caveat

Rovo MCP timings were bracketed with shell timestamps around each tool call
in an interactive session, so they include model turn-processing time
between calls, not pure API latency. The absolute Rovo numbers are
therefore inflated versus a clean benchmark harness. The relative gap
(CLI noticeably faster, fewer round-trips) held consistently across all
six steps and is not an artifact of the measurement method.

## Recommendation

Default to `atlassian-cli` for Jira/Confluence/Bitbucket operations. Reserve
Rovo MCP for things the CLI cannot do — e.g. Teamwork Graph relationship
queries (`getTeamworkGraphContext` / `getTeamworkGraphObject`).

## Known trap: Rovo MCP tenant lock-in

The locally-added Rovo MCP server (`claude mcp add --transport http
--scope user atlassian https://mcp.atlassian.com/v1/mcp/authv2`) picks the
Atlassian account from the browser's active session cookie on `/mcp`
login — no account picker is shown. If you are already logged into a
different Atlassian account in your browser, the OAuth flow silently signs
you into the wrong tenant, and `getAccessibleAtlassianResources` will show
that tenant's site instead of the one you intended.

Fix: log out of the other account in the browser (or use a private/incognito
window), log in explicitly with the account for the tenant you want, then
run `/mcp` again on the `atlassian` entry. Verify with
`getAccessibleAtlassianResources` before trusting any Rovo tool output.
