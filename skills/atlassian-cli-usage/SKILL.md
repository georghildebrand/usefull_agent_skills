---
name: atlassian-cli-usage
description: >
  Use when interacting with Jira, Confluence, or Bitbucket via atlassian-cli
  for issue updates, PR creation, richtext (ADF) descriptions, pipeline
  monitoring, or cross-profile / cross-org workflows. Covers the diagnostic
  flow for picking the right profile, ADF gotchas, pipeline watch usage, and
  harmless 204 parse-error false alarms on successful updates. For initial auth
  and profile creation, see the companion skill `atlassian-cli-setup`.
---

# atlassian-cli — Runtime Usage Patterns

Companion to `atlassian-cli-setup`. That skill covers initial auth, token
sourcing, profile creation. This skill covers what you run *after* profiles
exist — hard-won lessons on richtext descriptions, ADF, cross-org profile
selection.

## When To Use This Skill

- Profiles set up, need to *use* them.
- Hit confusing error, need to diagnose which profile/service at fault before
  touching credentials.
- Need non-trivial Jira description (headings, lists, code).
- Jira and Bitbucket in different Atlassian orgs, juggling multiple profiles
  per command.

First-time setup or recovering missing token → `atlassian-cli-setup` instead.

---

## Pick The Right Profile

Before re-login or guessing tokens, run:

```bash
atlassian-cli auth list
```

Table is hint, not final answer. Command fails → test target service directly
with intended profile.

Re-login only if relevant token missing or stale.

---

## Cross-Profile Workflow

Jira/Confluence and Bitbucket in different Atlassian orgs → tokens cannot be
shared. Each `atlassian-cli` profile usually belongs to one service family;
default profile often fails against the other.

### Identify the right Bitbucket profile for a repo

Checked-out repo → find workspace from git remote:

```bash
git remote get-url origin
# git@bitbucket.org:<workspace-slug>/<repo-slug>.git
```

Then list each Bitbucket-authenticated profile's identity:

```bash
atlassian-cli --profile <bitbucket-profile> bitbucket whoami
```

Profile whose account has access to `<workspace-slug>` is the one to use.
Workspace is **not** derived from Jira `base_url` host prefix.

### Cross-profile flag pattern

Place `--profile` **before** subcommand. Always.

Jira (Jira-authenticated profile):

```bash
atlassian-cli --profile <jira-profile> jira issue get <KEY>
```

Bitbucket (Bitbucket-authenticated profile) → pass both `--profile` **and**
`--workspace` explicitly on every command. Auto-detection is profile-bound, not
workspace-bound:

```bash
atlassian-cli --profile <bitbucket-profile> \
  bitbucket pr create <repo-slug> \
  --workspace <workspace-slug> \
  --source <feature-branch> \
  --destination main \
  --title "..." \
  --description "..."
```

### Common Failure Mode

Default-profile fallback silently selects wrong profile, reports
`Authentication failed: Invalid or expired credentials` against Bitbucket. Fix:
discover which profile holds the Bitbucket token, pass `--profile` explicitly.

---

## Bitbucket PR Create

### Subcommand name

Verb is **`pr`**, not `pullrequest`. Long form errors:

```
error: unrecognized subcommand 'pullrequest'
  tip: a similar subcommand exists: 'pr'
```

Sibling commands under `bitbucket pr`: `list`, `get`, `merge`, `decline`,
`approve`, `unapprove`, `diff`, `comment`. Discover flags via `--help`:

```bash
atlassian-cli bitbucket pr create --help
```

### Required arguments

| Form | What it is |
|---|---|
| `<REPO>` (positional, last) | Repo slug |
| `--title` | PR title |
| `--source` | Feature branch |
| `--destination` | Target branch (usually `main`) |
| `--workspace` | Workspace slug — required for cross-org, see profile section |

`--description`, `--reviewers <uuid,uuid>`, `-f json|yaml|markdown` optional but
useful. Reviewers take **UUIDs**, not usernames — find via `bitbucket whoami`
or `bitbucket workspace members` lookup.

### Flag-position gotchas

Same flag name can be valid at one CLI level, rejected at another. `--help` per
level is the only reliable map.

| Flag | Valid at top level<br>(`atlassian-cli`) | Valid at `bitbucket` group | Valid at `bitbucket pr create` |
|---|:-:|:-:|:-:|
| `--profile` | yes | no | no |
| `--workspace` | **no** | yes | yes |
| `--repo` | n/a | yes | **no — repo is positional here** |
| `--close-source-branch` | no | no | **not supported at all** |

Translation to working command:

```bash
atlassian-cli --profile <bitbucket-profile> \
  bitbucket --workspace <workspace-slug> \
  pr create <repo-slug> \
  --source <feature-branch> --destination main \
  --title "..." --description "..."
```

Or put `--workspace` on `pr create` instead of on `bitbucket` group — both
accepted. Pick one, stay consistent inside a script.

Error messages decode like this:

| Error | Cause | Fix |
|---|---|---|
| `unexpected argument '--workspace' found / tip: 'bitbucket --workspace' exists` | `--workspace` placed before `bitbucket` subcommand | Move after `bitbucket` (or after `pr create`) |
| `unexpected argument '--repo' found / tip: to pass '--repo' as a value, use '-- --repo'` | `--repo` used on `pr create` where repo is positional | Drop `--repo`, append `<repo-slug>` as last positional arg |
| `unexpected argument '--close-source-branch' found` | Flag does not exist on `pr create` | Configure "Close source branch after merge" as repo default in Bitbucket UI, or set via REST API after PR creation |

### Multi-line description via inline string

`--description` accepts literal string. Pass full markdown body inline between
quotes — works inside shell or `Bash` tool call. Backslash-escape any literal
`` ` `` inside fenced code blocks so shell does not treat them as command
substitution.

```bash
atlassian-cli --profile <bitbucket-profile> bitbucket pr create \
  --workspace <workspace-slug> \
  --source <feature-branch> \
  --destination main \
  --title "<TICKET> Short imperative title" \
  --description "## Summary

Bullet points.

## Why
...

## Validation
- step 1
- step 2" \
  <repo-slug>
```

### Success output

On success CLI prints single-line `INFO` log plus JSON object:

```
INFO Pull request created successfully pr_id=228 workspace="..." repo_slug="..."
{
  "destination": "main",
  "id": 228,
  "source": "fix/branch-name",
  "state": "OPEN",
  "title": "..."
}
```

PR URL not in output — construct as:
`https://bitbucket.org/<workspace>/<repo>/pull-requests/<id>`

### Mixed-ticket / stale-branch-name PRs

Branch opened for ticket A, stack ticket B's fix on top → title and description
reference both tickets explicitly. Branch name already pushed → note drift in PR
body, leave the branch.

---

## Subcommand naming gotchas (run `--help` when unsure)

| You might try | Actual name | Hint |
|---|---|---|
| `bitbucket pullrequest …` | `bitbucket pr …` | `tip: a similar subcommand exists: 'pr'` |
| `jira issue comment …` | `jira issue comments …` (plural) | `tip: a similar subcommand exists: 'comments'` |
| `jira issue comments add` | takes positional `<KEY>` last, `--body` required | discover with `--help` |

CLI emits `tip:` lines on `error: unrecognized subcommand` — trust them. Run
`<group> --help` before guessing.

---

## Jira Richtext Descriptions

`atlassian-cli jira issue update <KEY> --description "..."` only sends a
**single-paragraph plain-text ADF document**. Markdown, wiki markup, headings,
code blocks — none render. `--description` flag is plain text only.

For richtext (headings, lists, code blocks, inline marks, links), use `--field`
with full Atlassian Document Format (ADF) JSON object:

```bash
atlassian-cli --profile <jira-profile> jira issue update <KEY> \
  --field "description=$DOC_JSON"
```

Where `$DOC_JSON` is complete ADF document of shape:

```json
{"version": 1, "type": "doc", "content": [ /* block nodes */ ]}
```

This **works** — earlier guidance to avoid `--field` for ADF was wrong. Catch:
ADF must be valid and complete. Schema errors come back as `INVALID_INPUT` with
no further detail, so bisecting the document is the only debug path when
something is off.

ADF reference:
<https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/>

---

## Common ADF gotchas

- **Empty `content` arrays rejected.** A `bulletList`, `listItem`, `paragraph`,
  or any container with `content: []` fails whole document with `INVALID_INPUT`.
  Generators must skip nested container entirely when children empty, not emit
  empty array.
- **Tables inconsistently accepted via `--field` path.** ADF `table` nodes can
  be rejected with `INVALID_INPUT`. Workaround: render tables as bullet list,
  e.g. `**Header1:** value1 | **Header2:** value2 | ...` (use inline marks for
  headers).
- **`codeBlock` languages.** `text`, `makefile`, `yaml`, `bash`, `python`,
  `json` all accepted in practice. Stick to Atlassian's documented allow-list.
- **Inline marks.** `code`, `strong`, `em`, `link` work inside headings,
  paragraphs, list items.
- **Nested lists.** A `bulletList` may live inside a `listItem` alongside the
  item's `paragraph`, as long as nested list has at least one child.

---

## The harmless "error decoding response body" false alarm

On successful `jira issue update`, CLI prints:

```
ERROR Failed to parse JSON response: error decoding response body
Error: Failed to update issue <KEY>: Invalid response format: error decoding response body
```

**Harmless.** Jira returns `204 No Content` on successful PUT; CLI tries to
JSON-parse empty body and chokes. Ticket is updated.

Distinguish real failure from this false alarm:

| Message contains... | Meaning |
|---|---|
| `Invalid response format: error decoding response body` | False alarm — likely success, verify with GET |
| `Invalid request: {"errorMessages":[...]}` or similar JSON-from-Jira | Real failure — read message |

**Always verify with follow-up GET before reacting.** Same pattern applies to
`jira issue delete`.

---

## Python ADF builder helper

Copy-paste starting point for building ADF documents. Self-contained, no
dependencies. Handles empty-content-array gotcha by construction.

```python
import json

def text(s, *marks):
    node = {"type": "text", "text": s}
    if marks:
        node["marks"] = [{"type": m} for m in marks]
    return node

def h(level, body):
    """Heading. body = str or list of inline nodes."""
    content = [text(body)] if isinstance(body, str) else body
    return {"type": "heading", "attrs": {"level": level}, "content": content}

def p(*parts):
    """Paragraph. parts = strings or inline nodes."""
    content = [text(x) if isinstance(x, str) else x for x in parts]
    return {"type": "paragraph", "content": content}

def code_block(lang, body):
    return {"type": "codeBlock", "attrs": {"language": lang},
            "content": [{"type": "text", "text": body}]}

def bullet_list(items):
    """items: list of str, or list of (str, [sub-items]) for nested."""
    out = []
    for item in items:
        if isinstance(item, tuple):
            line, subs = item
            li = [{"type": "paragraph", "content": [text(line)]}]
            if subs:  # skip empty nested list — invalid in ADF
                li.append(bullet_list(subs))
            out.append({"type": "listItem", "content": li})
        else:
            out.append({"type": "listItem",
                        "content": [{"type": "paragraph",
                                     "content": [text(item)]}]})
    return {"type": "bulletList", "content": out}

def link(label, href):
    return {"type": "text", "text": label,
            "marks": [{"type": "link", "attrs": {"href": href}}]}

doc = {"version": 1, "type": "doc", "content": [
    h(2, "Heading"),
    p("Paragraph with ", text("bold", "strong"),
      " and ", text("code", "code"), "."),
    bullet_list([
        "one",
        "two",
        ("parent", ["child a", "child b"]),
    ]),
    code_block("python", "print('hi')"),
]}

print(json.dumps(doc))
```

---

## Shell invocation pattern

```bash
DOC=$(python3 build_adf.py)
atlassian-cli --profile <jira-profile> jira issue update <KEY> \
  --field "description=$DOC"

# Ignore "error decoding response body" — verify with:
atlassian-cli --profile <jira-profile> jira issue get <KEY> -f json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['description'][:300])"
```

---

## Jira issue transitions

Change ticket status via transitions (no `--status` flag).

```bash
atlassian-cli --profile <jira-profile> jira issue transition <KEY> --transition "<NAME>"
```

Common transitions: `"Done"`, `"In Progress"`, `"To Do"`. Discover per-project transitions via Jira UI or REST API.

**204 false alarm applies here too:**

```
ERROR Failed to parse JSON response: error decoding response body
Error: Failed to transition issue <KEY>: Invalid response format: error decoding response body
```

Verify transition succeeded by checking status:

```bash
atlassian-cli --profile <jira-profile> jira issue get <KEY> -f json | jq -r .status
```

---

## Verifying updates

204-empty-body quirk means `update`, `delete`, `transition` exit codes / stderr
are not reliable signals. **Always verify with a GET**:

```bash
# Update verification
atlassian-cli --profile <p> jira issue get <KEY>

# Delete verification — should return 404
atlassian-cli --profile <p> jira issue get <KEY>

# Status-specific verification (after transition)
atlassian-cli --profile <p> jira issue get <KEY> -f json | jq -r .status

# Description-specific verification
atlassian-cli --profile <p> jira issue get <KEY> -f json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('description'))"
```

---

## Monitoring Bitbucket pipelines

Use `pipeline watch` to block until pipeline completes. Requires `--profile`,
`--workspace`, `--repo`, `--pipeline` (pipeline number). Redirect stderr to
suppress noisy progress lines.

```bash
atlassian-cli --profile <bitbucket-profile> \
  bitbucket pipeline watch \
  --workspace <workspace-slug> \
  --repo <repo-slug> \
  --pipeline <pipeline-number> \
  2>/dev/null
```

Output on completion:

```
#42 SUCCESSFUL ✅ (feat/my-feature) [14:28]
```

**Key facts:**

- Blocks until pipeline finishes — safe to chain with `&&` for "wait then act".
- `2>/dev/null` suppresses streaming progress noise; final status line still prints to stdout.
- Pipeline number from Bitbucket UI or `bitbucket pipeline list` output.
- Use inside `/loop` wakeup when you need non-blocking polling instead.

```bash
# Find the latest pipeline number for a branch
atlassian-cli --profile <bitbucket-profile> \
  bitbucket pipeline list \
  --workspace <workspace-slug> \
  --repo <repo-slug> \
  --branch <branch-name>
```

---

## Jira issue types — use the right type

Match issue type to nature of work:

| Work type | `--issue-type` value |
|---|---|
| New feature / scope item | `"Story"` |
| Defect / regression | `"Bug"` |
| Sub-task under a Story | `"Sub-task"` |
| Epic | `"Epic"` |

**Do not default to `"Story"` for bugs.** Wrong type affects backlog
management, sprint metrics, velocity charts. User says "bug ticket" → use
`"Bug"`.

---

## Jira sprint assignment — look up the internal ID, never guess

Sprint assignment uses `customfield_10020`, requires **Jira-internal integer
sprint ID** — not human-readable sprint sequence number shown in UI (e.g.
"Sprint 53").

```bash
# When creating or updating an issue, assign to sprint like this:
atlassian-cli --profile <jira-profile> jira issue create ... \
  --field 'customfield_10020=[{"id":<SPRINT_INTERNAL_ID>}]'
```

**UI sprint number and internal ID are completely different.** Never iterate or
guess — always look up ID fresh via Jira Agile REST API:

```bash
# Find the active sprint internal ID for a board
curl -s \
  -u "<email>:<jira-api-token>" \
  "https://<your-instance>.atlassian.net/rest/agile/1.0/board/<BOARD_ID>/sprint?state=active" \
  | python3 -c "
import sys, json
for s in json.load(sys.stdin)['values']:
    print(s['id'], s['name'])
"
```

Board ID visible in Jira board URL:
`https://<your-instance>.atlassian.net/jira/software/projects/<PROJECT>/boards/<BOARD_ID>`.

`atlassian-cli` has no built-in sprint listing command — REST API call above is
the only reliable path.

---

## Jira REST API fallback — attachments and full comment body

`atlassian-cli` does not expose attachment metadata, truncates comment bodies
to 50-char preview. Use Jira REST API v3 directly when you need either. Auth via
`ATLASSIAN_API_TOKEN` sourced from `~/.env.atlassian`.

**Never read `~/.env.atlassian` — source it:**

```bash
source ~/.env.atlassian
# provides ATLASSIAN_API_TOKEN, ATLASSIAN_EMAIL, ATLASSIAN_INSTANCE (or set manually)
```

### List attachments on an issue

```bash
source ~/.env.atlassian
curl -s -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<your-instance>.atlassian.net/rest/api/3/issue/<KEY>?fields=attachment" \
  | python3 -c "
import json, sys
for a in json.load(sys.stdin)['fields'].get('attachment', []):
    print(f\"{a['id']} | {a['filename']} | {a['mimeType']} | {a['size']}B | {a['content']}\")
"
```

### Download an attachment

```bash
source ~/.env.atlassian
curl -s -L -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<your-instance>.atlassian.net/rest/api/3/attachment/content/<ATTACHMENT_ID>" \
  -o /tmp/<filename>
```

`-L` required — Jira returns 302 redirect to CDN URL.

### Read full comment body

```bash
source ~/.env.atlassian
curl -s -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<your-instance>.atlassian.net/rest/api/3/issue/<KEY>/comment/<COMMENT_ID>" \
  | python3 -c "
import json, sys
def text(n):
    if n.get('type') == 'text': return n.get('text','')
    if n.get('type') == 'mention': return n['attrs'].get('text','')
    if n.get('type') == 'hardBreak': return '\n'
    r = ''.join(text(c) for c in n.get('content', []))
    if n.get('type') in ('paragraph','heading','listItem'): r += '\n'
    return r
print(text(json.load(sys.stdin)['body']))
"
```

Comment body is Atlassian Document Format (ADF) — nested JSON AST. Direct string
access fails; recursive `text()` walk above is correct pattern.

### Comment IDs

Get from `atlassian-cli jira issue comments list <KEY> --format json` — the
`id` field.

---

## Native CLI support (after PR #64 merges)

PR [omar16100/atlassian-cli#64](https://github.com/omar16100/atlassian-cli/pull/64)
adds both features to CLI directly:

```bash
# Attachments in issue get (all non-markdown formats)
atlassian-cli jira issue get <KEY> --format json | jq '.attachments'

# Full comment body
atlassian-cli jira issue comments list <KEY> --full --format json
```

Until merged, use REST API patterns above.

---

## Cross-references

- `atlassian-cli-setup` — first-time auth, token sourcing, profile creation,
  recovery when Bitbucket login overwrites Jira token.
- ADF spec: <https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/>
- Jira REST API (issue): <https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/>
- Confluence Storage Format: <https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html>
