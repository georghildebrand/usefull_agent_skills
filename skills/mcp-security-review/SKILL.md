---
name: mcp-security-review
description: Use when reviewing, threat-modeling or hardening an MCP (Model Context Protocol) server, client, host configuration, gateway or proxy - a FastMCP or SDK server file, an mcpServers JSON config, a remote MCP endpoint, a plan to install a community MCP server, or a design for a multi-tenant MCP service. Also when someone asks "is this MCP server safe", about tool poisoning, prompt injection through tools, token passthrough, confused deputy, DNS rebinding, shadow MCP servers or denial of wallet.
---

# MCP security review

## Overview

An MCP review is not a normal code review. In MCP an LLM decides which tool runs and with
which arguments, and the LLM reads text that attackers can write. So two rules hold for every
finding:

1. **Everything an MCP server returns is untrusted input**: tool names, descriptions and
   schemas from `tools/list`, tool results, resources, prompts, elicitation requests.
2. **Security lives in the tool code and in the host configuration, never in the model.**
   A tool that is safe only "if the model calls it correctly" is unsafe.

The skill uses the CoSAI threat taxonomy (twelve categories, MCP-T1 to MCP-T12, 34 numbered
threats). Full catalog with controls: [references/cosai-threat-catalog.md](references/cosai-threat-catalog.md).

## Procedure

### 1. Classify the deployment pattern first

| Pattern | How to recognise it | What dominates the review |
|---|---|---|
| DP1 all-local | `command`/`args` entries in the client config, stdio, or HTTP on localhost | Server runs with the user's rights: sandbox, supply chain, DNS rebinding if HTTP |
| DP2 single-tenant remote | `url` entry, one server instance per user or team | Auth between client and server, token storage, TLS |
| DP3 multi-tenant | One server or one database serves several customers or teams | Tenant isolation in every tool, identity, per-object authorization |

One review often covers several patterns: a client config mixes local and remote servers.
Classify each server. A server that serves more than one team or customer is DP3, even when
it runs on a private network.

### 2. Map the tool surface

For each server list: tools, whether each tool reads, writes or deletes, which credentials it
holds, and which tools return text that someone outside the team can write (customer notes,
emails, documents, web pages, PDFs, issue comments).

### 3. Check across servers in the same host

All servers in one client share one model context. Write down every pair where **untrusted
text from server A can reach the model** and **server B has a tool that writes, deletes,
sends data out or runs code**. Each pair is a risk (threats 4, 11; categories T4, T9), even
if each server alone looks fine. Single-file reviews miss this. A tool of one server that
returns untrusted text, next to a destructive tool of the same server, is the same path.

List these pairs only in the "Cross-server paths" section of the report. Add one finding
that points to that section when at least one path exists.

### 4. Walk all twelve categories

Use the check list below. The signals are things to grep for or to look at; they are
examples, not the full list.

| ID | Check | Signals in code or config |
|---|---|---|
| T1 auth and identity | Is every request authenticated? Can the chain user → server → downstream be traced? Where are credentials stored? | No auth on an HTTP server; static API keys; tokens in plain config or env of a third-party process |
| T2 access control | Per-object and per-tenant checks inside each tool? Scopes minimal? | Tenant or user id taken from tool arguments instead of the verified identity; one database or folder for all tenants; write scope for a read tool |
| T3 input validation | Classic injection in tool code | `shell=True`, f-string SQL, `os.path.join` without resolving and checking the result, unencoded ids in URLs, unsafe deserialization |
| T4 instruction/data boundary | Which tool results, descriptions or resources carry attacker text into the context? | Docstrings or descriptions that say "free text", "notes", "comments", "email body"; tools that fetch web pages or documents |
| T5 data protection | Sensitive data in results, logs, error messages; encryption at rest and in transit | Raw exceptions returned to the client; full records returned when two fields are needed |
| T6 integrity | Can tool definitions or config change after approval without anyone noticing? | Unpinned packages (`@latest`, no version): each start can bring new tool definitions, so this counts under T6 and T11; config files writable by the server; tools with names close to other servers' tools |
| T7 session and transport | TLS, session binding, Origin check, CSRF, CORS on HTTP transports | `http://` URLs to remote servers; no `Origin` validation; session id in URL |
| T8 network binding | Bound to all interfaces? Reachable from a browser page (DNS rebinding)? Outbound network open? | `host="0.0.0.0"`; local HTTP server without auth; no egress limit |
| T9 trust and tool design | Powerful generic tools that trust the model; risky actions without a confirmation the user cannot switch off | "Run any SQL", "run any command", delete or send tools with no confirmation or elicitation |
| T10 resource limits | Payload size, recursion depth, call rate, row limits, cost limits | No `LIMIT`, no timeout on subprocess or HTTP, no rate limit per caller |
| T11 supply chain and lifecycle | Where does each server come from, is it pinned, inventoried, approved, retired? | `npx -y pkg@latest`, `uvx pkg` without version, unofficial wrapper of a vendor API, no allowlist |
| T12 logging and audit | Is it logged which tool ran, with which arguments, after which prompt, under which identity? | No log at all; logs without caller identity; logs that contain secrets |

### 5. Write the report in this shape

```markdown
## MCP security review: <target>

Deployment pattern: <DP1 | DP2 | DP3 per server, one line each>

### Findings (most severe first)
1. [critical | high | medium | low] [MCP-T<n>] <file:line or config key> - <problem in one or two sentences>
   Fix: <concrete change>

### Cross-server paths
- <server A tool> returns <untrusted text> -> model -> <server B tool> can <write/delete/exfiltrate>
  (or: "none found, because <reason>")

### Category coverage
| ID | Status | Note |
|---|---|---|
| T1 | finding / ok / not examined / n/a | <one line> |
... one row for each of T1 to T12, none skipped

### Not examined
- <what the files did not show: deployment, gateway, IdP config, package contents, ...>

### Other issues (optional)
- <bugs that are not security findings, for example a framework misuse that breaks a tool>
```

Every row T1 to T12 is required. "not examined" and "n/a" are valid statuses; an empty row
is not. Use "ok" only when you saw the control, not when you saw no problem.

Severity:

- **critical** - an unauthenticated caller, or text from outside the team, can read other
  tenants' data, delete or change data, or run code.
- **high** - the same damage, but it needs a valid user or a second step.
- **medium** - the problem widens other attacks or leaks limited data (no limits, raw
  errors, unpinned packages).
- **low** - hardening that is missing, but no direct way to cause damage.

The category ID `MCP-T<n>` is required. A threat number from the catalog (`threat 21`) is
optional: add it only after you looked it up in the reference file.

## Fixes the catalog recommends most often

- Replace generic tools with purpose-built ones: a fixed, parameterized query instead of
  "run any SQL"; a list of arguments instead of a shell string.
- Take tenant and user from the verified token, never from tool arguments.
- No token pass-through: the server exchanges the user's token for a token meant for the
  downstream service (OAuth token exchange, RFC 8693) with minimal scopes, short lifetime.
- Destructive actions need a confirmation the user cannot switch off: a locked host
  configuration, or a server-side elicitation request.
- Local servers: stdio over local HTTP; sandbox servers that touch files, commands or the
  network (a plain container is a weak boundary).
- Remote servers: TLS, authentication, `Origin` check, bind to a private interface behind a
  proxy, payload and rate limits.
- Supply chain: pin exact versions or hashes, prefer the server run by the service vendor
  itself, keep an allowlist and an inventory with owner and version.
- Log tool name, arguments, caller identity and the triggering prompt; a gateway can do this
  in one place.

## Common mistakes

| Mistake | Correction |
|---|---|
| Review only `server.py` and ignore the client config | The config decides which other servers share the context (step 3) |
| Treat tool descriptions of third-party servers as documentation | They are input the model obeys; they can change after approval (threats 2, 3, 32) |
| "The model will refuse dangerous calls" | Threat 7: model refusals can be bypassed, and the model can be replaced |
| "Users confirm every call" | Threat 13: users approve without reading when prompts are frequent; hosts let users switch confirmation off |
| Report only what is broken | The coverage table shows which categories were checked and which were not |

## Keeping review output safe to share

Reviews often look at files that contain credentials. Cite the location (`config.json`, key
`mcpServers.<server-name>.env`) and the kind of secret, never the value. Write example tokens as
`<token>` placeholders. A secret value copied into a report or ticket is a new leak, and
local secret scanners will block the report file later.

## Related skills

- `search-coverage-reporting` - for the "Not examined" section.
- `repo-install-safety-check` - before installing a community MCP server from a repository.
