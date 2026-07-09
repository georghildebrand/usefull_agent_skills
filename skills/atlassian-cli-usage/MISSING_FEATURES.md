# atlassian-cli — Missing Features & Gaps

Central register of features missing from `atlassian-cli` (omar16100/atlassian-cli), collected during day-to-day use. Each entry has enough context to file as an upstream issue without re-investigation. When a gap is filed upstream, mark it `Filed:` with the issue URL; when fixed, mark `Resolved:` with the version/commit.

**Upstream issue title convention:** must start with `[FEATURE]` (per upstream contribution guidance).

**Filing principle:** group gaps that share a theme into one issue (e.g. Confluence parity gaps go together); split when the upstream maintainer asks.

---

## Status legend

- 🔴 **Open** — observed, not yet filed
- 🟡 **Filed** — issue exists upstream, awaiting response
- 🟢 **Resolved** — landed; can be deleted from this file at next cleanup pass

---

## Gap 1 — `confluence page comments` only returns footer comments 🔴

**Observed:** `atlassian-cli confluence page comments <PAGE_ID>` returns empty `[]` for a page that actually has inline (text-anchored) comments.

**Root cause:** Confluence Cloud REST API v2 exposes footer and inline comments as separate resources; the CLI subcommand appears to call only the footer endpoint.

- `GET /wiki/api/v2/pages/{id}/footer-comments`
- `GET /wiki/api/v2/pages/{id}/inline-comments`

**Why it matters:** Inline comments are how most review feedback actually happens. The omission turns "I'll just fetch the comments" into a curl detour.

**Proposed fix:**
- Add `--inline` / `--footer` flags (default: include both, with a `type` column in tabular output).
- JSON output per comment: `id`, `type`, `authorId`, `createdAt`, `status` (current/resolved), `inline-marker-ref`, `inline-original-selection`, `body.storage.value`.

**Workaround today:**
```bash
source ~/.env.atlassian
curl -s -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<instance>.atlassian.net/wiki/api/v2/pages/<id>/inline-comments?body-format=storage&limit=100"
```

---

## Gap 2 — `--format markdown` corrupts `ac:structured-macro` code blocks 🔴

**Observed:** `confluence page get <id> --format markdown` (or `--body-only --format markdown`) renders `ac:structured-macro ac:name="code"` blocks with macro attribute values like `breakoutMode="wide"` + `breakoutWidth="760"` concatenated into a stray leading token (`textwide760…`), and multiline CDATA bodies sometimes collapse onto a single line.

**Root storage XHTML is intact** — only the markdown projection is broken. Reader concludes "page is corrupted" — it isn't.

**Proposed fix:**
- Emit triple-backtick fences with the macro's `language` parameter; pass CDATA through unchanged (newlines preserved).
- Drop styling-only macro attributes (`breakoutMode`, `breakoutWidth`) from the markdown body.

**Workaround today:** use `--format json` and read `body.storage.value` for source-of-truth, OR use `--body-only` alone which returns raw storage XHTML (apparently `--body-only` overrides `--format` — itself a quirk worth documenting).

---

## Gap 3 — No `confluence page move` subcommand 🔴

**Observed:** `atlassian-cli confluence page` has no `move` verb. Re-parenting (same space) and cross-space moves both require dropping to:

```
PUT /wiki/rest/api/content/{pageId}/move/{position}/{targetId}
```

Cross-space moves additionally require space-admin permissions on the target space, but the CLI can't even attempt the call.

**Proposed fix:**
- `atlassian-cli confluence page move <PAGE_ID> --target <TARGET_PARENT_ID> [--position append|before|after]`.
- Surface a clear permission error (parse the 403 body) rather than the raw JSON.

---

## Gap 4 — `confluence page create` does not print the page URL 🔴

**Observed:** On success the CLI prints:

```
INFO Page created successfully id=6840615064 title=My Page Title
✅ Created page: My Page Title (ID: 6840615064)
```

URL is reconstructable from space key + page ID, but `--space` takes the space *ID* at create time, not the key — requires a second lookup.

**Proposed fix:**
- Emit `url: https://<instance>/wiki/spaces/<SPACE_KEY>/pages/<page_id>` on a third line.
- Alternative: `--url-only` mode for scripting (suppresses INFO line).

---

## Gap 5 — `--id` vs positional `<PAGE_ID>` inconsistency across `confluence page` subcommands 🔴

**Observed:**

| Subcommand | PAGE_ID form |
|---|---|
| `confluence page get` | **Positional** `<PAGE_ID>` (using `--id` errors with "unexpected argument") |
| `confluence page update` | **Positional** `<PAGE_ID>` |
| `confluence page delete` | **Flag** `--id <PAGE_ID>` |

Documented in the skill already, but it's a footgun for any reflexive user who used one subcommand first.

**Proposed fix:** converge to positional for all three; `delete` accepts positional, `--id` deprecated.

---

## Gap 6 — `jira issue comment` singular subcommand missing (only `comments` works) 🔴

**Observed (2026-06-16):**

```
$ atlassian-cli jira issue comment add PROJ-450 --body "..."
error: unrecognized subcommand 'comment'
  tip: a similar subcommand exists: 'comments'
```

The CLI does suggest the correct form, so this is a low-impact UX papercut. But every Jira CLI I've used uses *singular* (`comment add`, `comment list`) and that's the muscle-memory default.

**Proposed fix:** add `comment` as an alias for `comments` (clap alias derive); both work, docs mention `comments` as canonical.

---

## Gap 7 — No way to trigger a Bitbucket pipeline's manual step from the CLI 🔴

**Observed (2026-06-16, during P1 recovery):**

A Bitbucket pipeline with a manual gate (e.g. `bitbucket-pipelines.yml:167-186` for our prod deploy) cannot be advanced past the gate via `atlassian-cli`. `bitbucket pipeline trigger` *starts* a new pipeline, but does not continue an existing one paused at a manual step. The only path is the Bitbucket web UI, which is bad for incident automation and bad for CI-driven workflows.

**Why it matters:** during an outage you want to push a single command (`atlassian-cli bitbucket pipeline step continue 1238 --step-uuid <step-id>`) and capture the pipeline ID for downstream watching. The web-UI detour breaks the loop.

**Proposed fix:**
- Add `atlassian-cli bitbucket pipeline step continue <PIPELINE_ID> --step-uuid <UUID>` (or `--step-name`).
- Companion: `bitbucket pipeline step list <PIPELINE_ID>` so callers can find the paused step UUID/name programmatically.

**Workaround today:** trigger via web UI; capture pipeline number; pipe into `atlassian-cli bitbucket pipeline watch` for completion-tracking.

---

## Gap 8 — `--field 'parent={"key":"..."}'` silently dropped on Story create/update when parent isn't on the project's screen 🔴

**Observed (2026-06-17, PROJ project on a Jira Cloud instance):**

```
$ atlassian-cli jira issue create \
    --project PROJ --issue-type "Story" \
    --summary "..." --description "..." \
    --field 'parent={"key":"PROJ-68"}'
INFO Issue created successfully key=PROJ-463
✅ Created issue: PROJ-463

$ atlassian-cli jira issue update PROJ-463 --field 'parent={"key":"PROJ-68"}'
ERROR Failed to parse JSON response: error decoding response body  # known 204 false alarm

# Verify
$ atlassian-cli jira issue search --jql "key = PROJ-463" -f json | jq '.[].parent'
null  # parent NEVER set — silently dropped on both create AND update
```

Subsequent JQL `parent = PROJ-68` confirms the issue is orphaned.

Root cause: the PROJ project's Story issue type doesn't have the `parent` field on its create/edit screen (workflow-configured restriction). Jira accepts the API call but ignores the `parent` value, returning success without setting it. The CLI relays the success and the caller has no signal that the linkage failed.

REST PUT directly to `/rest/api/3/issue/<KEY>` with `{"fields":{"parent":{"key":"..."}}}` also fails (`404` "Issue does not exist or you do not have permission to see it.") — the modern `parent` field is screen-permission-gated too.

**Why it matters:**
- Programmatic ticket creation cannot establish epic linkage without manual UI follow-up.
- Tickets are silently orphaned. Epic boards and "what's under X epic" reports miss them entirely until someone notices.
- No error signal at any layer — CLI exits 0, response body parses, status code is 2xx. Pure silent failure.
- Affects every cross-org Jira instance with workflow-restricted Story creation screens (common in mature setups).

**Proposed fix:**
- Issue-create response should surface the **persisted** parent value, not just the request. Emit `parent: PROJ-68` on success, `parent: null` if dropped — caller can fail-fast.
- If the create-screen config rejects a passed `--field`, surface a structured warning: `WARN '--field parent' silently dropped: Story type has no 'parent' field on the create screen for project PROJ.`
- Alternative: pre-check via `GET /rest/api/3/issue/createmeta?projectKeys=<P>&issuetypeNames=<T>&expand=projects.issuetypes.fields` before submitting; refuse the call if the supplied `--field` isn't in the meta.
- Companion `--strict-fields` flag for callers that want the call to **fail** rather than warn when a field is silently dropped.

**Workaround today:**
- After every programmatic create/update with `--field parent`, verify via JQL: `atlassian-cli jira issue search --jql "parent = <EPIC> AND key = <NEW_KEY>"`. Empty result = parent didn't stick → manual UI reparent.
- For known-affected projects, skip `--field 'parent='` at create time entirely; create first, then reparent via UI.

---

## Gap 9 — `jira issue get` output omits `parent` field even when set 🔴

**Observed (2026-06-18, PROJ project on a Jira Cloud instance):**

```
$ atlassian-cli jira issue create \
    --project PROJ --issue-type "Sub-task" \
    --summary "..." --description "..." \
    --field 'parent={"key":"PROJ-454"}'
INFO Issue created successfully key=PROJ-471
✅ Created issue: PROJ-471

# Verify parent linkage — GET shows no parent
$ atlassian-cli jira issue get PROJ-471 -f json | jq '.parent'
null

# But JQL confirms parent IS set correctly
$ atlassian-cli jira issue search --jql "parent = PROJ-454 AND key = PROJ-471"
PROJ-471 found ✓
```

The Sub-task's parent linkage was set correctly by the create call — JQL search confirms it — but `jira issue get` JSON output does not include the `parent` field in its default response. Same behavior across 5 newly-created Sub-tasks in one batch.

**Distinct from Gap 8:** Gap 8 = `--field parent` *silently dropped* on screen-gated Stories (parent never set). Gap 9 = parent IS set but GET *doesn't show it* (observability gap). Both can hit simultaneously, which is the worst case — the caller can't tell which failure they're seeing.

**Why it matters:**
- Verification after every parent-setting call requires a JQL roundtrip — extra request per ticket, extra latency in workflows that file many tickets in parallel.
- Workflow agents must encode "GET is unreliable for parent — always use JQL" as tribal knowledge. Easy to forget.
- Combined with the Gap 8 silent-drop class, the only authoritative parent check is JQL. The natural CLI affordance (`issue get`) lies by omission.
- Affects any orchestration that files Sub-tasks/Stories and needs to verify epic linkage programmatically (e.g. post-mortem follow-up automation, sprint-prep ticket batching, restructure migrations).

**Proposed fix:**
- Include `parent` as a top-level field in `jira issue get` JSON output (alongside `assignee`, `reporter`, `status` etc.) — populated from `fields.parent.key` when present, `null` otherwise.
- Mirror in tabular output as a `parent` column (omit when `null` if it clutters; show when set).
- Companion: `--include parent` / `--fields parent,status,assignee` flag for explicit field selection on GET, consistent with Jira REST API's `fields` query parameter.

**Workaround today:**
```bash
# Verify parent after create
atlassian-cli jira issue search --jql "parent = <EXPECTED_PARENT> AND key = <NEW_KEY>" -f json \
  | jq 'length > 0'
# returns true if parent linkage is set, false otherwise
```

For batch verification, build a single JQL:
```bash
atlassian-cli jira issue search --jql "key in (PROJ-470, PROJ-471, PROJ-473) AND parent = PROJ-454"
```

---

## Gap 10 — `jira issue get` does not expose the `resolution` field; `update --field resolution=` unverifiable via CLI 🔴

**Observed (2026-06-23, PROJ project on a Jira Cloud instance):**

```
# Transition tickets to Done, then try to set resolution
$ atlassian-cli --profile myorg jira issue update PROJ-410 \
    --field 'resolution={"name":"Won'\''t Do"}'
ERROR Failed to parse JSON response: error decoding response body  # known 204 false alarm

# Verify — resolution field absent from get output
$ atlassian-cli --profile myorg jira issue get PROJ-410 -f json | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(list(d.keys()), d.get('resolution'))"
['assignee', 'attachments', 'description', 'issue_type', 'key', 'reporter', 'status', 'summary'] None
```

`resolution` is not in the field list returned by `jira issue get`, so the caller cannot distinguish between:
- Update silently succeeded (resolution set but not surfaced)
- Update silently failed (resolution rejected, field ignored)

Verification requires a direct REST API call:

```bash
source ~/.env.atlassian
curl -s -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<instance>.atlassian.net/rest/api/3/issue/PROJ-410?fields=resolution" \
  | python3 -c "import json,sys; r=json.load(sys.stdin)['fields'].get('resolution'); print(r['name'] if r else 'unresolved')"
```

**Background — resolution vs status:** In Jira, *status* is the workflow state ("Done", "In Progress"); *resolution* is why the ticket closed ("Fixed", "Won't Do", "Duplicate"). Many projects have no `"Won't Do"` workflow **transition** — closing via resolution is the intended mechanism. The CLI has no built-in path for that.

**Why it matters:**
- "Close as Won't Do" is a common triage operation; callers resort to REST API for something that should be a one-liner.
- The 204 false alarm pattern means `update --field resolution=` always *looks* like success. The field being absent from GET compounds this — there is no fast CLI path to confirm the update landed.
- Affects any workflow that closes multiple tickets with specific resolutions (triage sweeps, sprint cleanup, deprecation scripts).

**Proposed fix:**
- Include `resolution` as a top-level field in `jira issue get` JSON output (value `null` when unset, `"Won't Do"` / `"Fixed"` / etc. when set).
- Add `--resolution <NAME>` flag to `jira issue transition` so resolution can be set atomically with the status transition (mirrors the Jira REST API's `fields` block inside a transition payload).
- Bonus: `jira issue update --resolution <NAME>` standalone flag (same as `--field resolution={"name":"..."}` but ergonomic).

**Workaround today:**
```bash
# Set resolution via --field (fires, unverifiable via CLI)
atlassian-cli --profile <p> jira issue update <KEY> \
  --field 'resolution={"name":"Won'\''t Do"}'

# Verify via REST API (requires ~/.env.atlassian sourced)
source ~/.env.atlassian
curl -s -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<instance>.atlassian.net/rest/api/3/issue/<KEY>?fields=resolution" \
  | python3 -c "import json,sys; r=json.load(sys.stdin)['fields'].get('resolution'); print(r['name'] if r else 'unresolved')"
```

---

## Gap 11 — Bitbucket subcommand flag/positional & flag-ordering inconsistencies 🔴

**Observed (2026-06-17 … 2026-06-23, profile `otherorg`, workspace `otherorg-workspace`):**

The Bitbucket subtree disagrees with the rest of the CLI about where flags go and which inputs are flags vs positionals. Four distinct papercuts, same root (inconsistent clap arg model across subcommands):

```
# (a) Global --profile rejected when placed AFTER the subcommand
$ atlassian-cli bitbucket pr create --profile otherorg --workspace ... <REPO> ...
error: unexpected argument '--profile' found
  tip: to pass '--profile' as a value, use '-- --profile'
# --profile is a GLOBAL flag and must precede `bitbucket`; the tip is misleading.

# (b) --workspace rejected when placed BEFORE the subcommand
$ atlassian-cli --workspace ... bitbucket pr get ...
error: unexpected argument '--workspace' found
  tip: 'bitbucket --workspace' exists
Usage: atlassian-cli --profile <PROFILE> <COMMAND>
# --workspace is a bitbucket-LOCAL flag and must come AFTER `bitbucket`.
# Net effect: --profile goes before `bitbucket`, --workspace goes after. Opposite rules, same command.

# (c) pr get / pr create take REPO as a positional, reject --repo / --repository
$ atlassian-cli bitbucket pr get --repo <REPO> ...
error: unexpected argument '--repo' found
  tip: to pass '--repo' as a value, use '-- --repo'
Usage: atlassian-cli bitbucket pr get --workspace <WORKSPACE> <REPO> <PR_ID>
$ atlassian-cli bitbucket pr list --repository <REPO>
error: unexpected argument '--repository' found
# Jira uses --project; Bitbucket uses a bare positional <REPO>. No --repo alias anywhere.
```

**Why it matters:**
- The documented Jira pattern `atlassian-cli --profile <p> jira ...` does NOT transfer to Bitbucket — `--profile` before, `--workspace` after, `<REPO>` positional. Every cross-org Bitbucket call is trial-and-error.
- The `tip: to pass '--profile' as a value, use '-- --profile'` is actively wrong advice for a global flag in the wrong position — it sends users down a dead end.

**Proposed fix:**
- Accept `--profile` and `--workspace` in EITHER position (global flags should be position-independent; clap `global = true`).
- Add `--repo` / `--repository` as accepted aliases for the positional `<REPO>` on all `bitbucket pr` / `bitbucket pipeline` subcommands.
- Fix the misleading `'-- --profile'` tip when the token is a known global flag in the wrong slot — suggest moving it before the subcommand instead.

**Workaround today:** `--profile` before `bitbucket`; `--workspace` after `bitbucket`; pass repo slug as the trailing positional, never `--repo`.

---

## Gap 12 — `bitbucket pipeline get <BUILD_NUMBER>` rejects the numeric build number 🔴

**Observed (2026-06-17, 2026-06-22):**

```
$ atlassian-cli bitbucket pipeline get 1250
error: unexpected argument '1250' found
Usage: atlassian-cli bitbucket pipeline get [OPTIONS] [PIPELINE_ID]
# --help advertises:  Arguments: [PIPELINE_ID]  Pipeline UUID or build number
```

The help text says `[PIPELINE_ID]` accepts a "UUID or build number", and the slot is an optional positional — yet passing the build number `1250` is rejected as an unexpected argument. So the one identifier a caller actually has from `pipeline list` / a webhook (the integer build number) is the one form `get` won't take.

**Note / possible confound:** in at least one occurrence this co-occurred with the Gap 11(b) `--workspace` ordering problem, which can make clap misattribute the positional. Worth reproducing in isolation upstream — but the help-vs-behavior contradiction (`build number` documented, integer rejected) stands on its own.

**Why it matters:** the build number is the natural handle during an incident (`pipeline list` prints it, the Bitbucket URL contains it). Forcing a UUID lookup first breaks `list → get → watch` automation.

**Proposed fix:**
- Accept the integer build number on `pipeline get` exactly as `--help` promises; if a leading-`-` parse ambiguity is the cause, document `pipeline get -- 1250` or add `--build <N>`.
- If only UUIDs are truly supported, fix the `--help` text and emit `error: build numbers not supported, use the pipeline UUID` instead of the generic clap message.

**Workaround today:** resolve the UUID via `pipeline list` JSON, or fall back to the web UI / `rest/api` for the build.

---

## Gap 13 — `bitbucket pipeline step-log` missing (no per-step log retrieval) 🔴

**Observed (2026-06-24):**

```
$ atlassian-cli bitbucket pipeline step-log <PIPELINE_ID> <STEP_UUID>
error: unrecognized subcommand 'step-log'
  tip: some similar subcommands exist: 'stop', 'steps'
Usage: atlassian-cli bitbucket pipeline [OPTIONS] <COMMAND>
```

`pipeline steps` lists steps; `pipeline stop` halts; but there is no verb to fetch a *step's log output*. Diagnosing a failed CI step from the CLI is impossible — you must open the web UI.

**Distinct from Gap 7:** Gap 7 = advance a pipeline past a manual gate (write). This = read a step's log (observability). Both belong to a "complete the Bitbucket pipeline step surface" theme.

**Proposed fix:** `atlassian-cli bitbucket pipeline step-log <PIPELINE_ID> --step-uuid <UUID>` (or `--step-name`) →
`GET /2.0/repositories/{ws}/{repo}/pipelines/{id}/steps/{step_uuid}/log`. Stream to stdout for piping into `grep`/`tail`.

**Workaround today:** web UI, or curl the pipeline-step log REST endpoint directly.

---

## Gap 14 — `jira issue search` has no `--fields` selection (full issue always fetched) 🔴

**Observed (2026-06-24):**

```
$ atlassian-cli jira issue search --jql "project = PROJ AND parent = PROJ-68" --fields key,status,parent
error: unexpected argument '--fields' found
Usage: atlassian-cli jira issue search --jql <JQL> --format <FORMAT>
```

`jira issue search` accepts only `--jql` / `--format`; there is no way to project a subset of fields. The same `--fields` gap exists on `jira issue get` (see Gap 9/10). The Jira REST API natively supports a `fields` query param — the CLI doesn't surface it on either read path.

**Why it matters:**
- Bulk JQL sweeps (sprint prep, epic audits, restructure migrations) over-fetch every field for every issue — slower, larger payloads, more to parse.
- No way to pull a field that the default projection omits (e.g. `parent`, `resolution` from Gaps 9/10) — so the only fix for those omissions today is REST.

**Proposed fix:** add `--fields <comma-list>` to BOTH `jira issue search` and `jira issue get`, passed straight through to the REST `fields` param. Default projection unchanged when omitted. (Ties Gap 9 + Gap 10 + Gap 14 into one read-path field-selection fix.)

**Workaround today:** REST `GET /rest/api/3/search?jql=...&fields=key,status,parent`, or fetch all and filter with `jq`.

---

## Gap 15 — No Jira sprint listing / sprint-ID lookup command 🔴

**Observed (2026-06-24):**

Assigning an issue to a sprint requires the sprint's *internal numeric ID*:

```
$ atlassian-cli jira issue update <KEY> --field 'customfield_10020=[{"id":<SPRINT_INTERNAL_ID>}]'
```

…but there is no `atlassian-cli jira sprint list` (or `board list`) to discover that ID. The only path is the Agile REST API:

```bash
source ~/.env.atlassian
curl -s -u "${ATLASSIAN_EMAIL}:${ATLASSIAN_API_TOKEN}" \
  "https://<instance>.atlassian.net/rest/agile/1.0/board/<BOARD_ID>/sprint?state=active" \
  | python3 -c "import sys,json; [print(s['id'], s['name']) for s in json.load(sys.stdin)['values']]"
```

**Why it matters:** sprint assignment is a routine triage/planning op, but it's gated behind a non-obvious `customfield_10020` magic field AND a REST roundtrip to find the sprint ID. Pure web-UI/REST territory for something that should be `jira sprint add <KEY> --sprint "Sprint 23"`.

**Proposed fix:**
- `atlassian-cli jira board list [--project <P>]` → board IDs + names.
- `atlassian-cli jira sprint list --board <ID> [--state active|future|closed]` → sprint IDs + names + dates.
- `atlassian-cli jira sprint add <ISSUE_KEY> --sprint <ID|name>` ergonomic wrapper over the `customfield_10020` write.

**Workaround today:** Agile REST API as above to find the sprint ID; then `--field 'customfield_10020=[{"id":N}]'`.

---

## Gap 16 — `jira issue update` lacks `--issue-type` (only `create` has it); no in-place type change 🔴

**Observed (2026-06-24):**

```
$ atlassian-cli jira issue update PROJ-508 --field 'parent={"key":"PROJ-68"}' --issue-type "Story"
error: unexpected argument '--issue-type' found
  tip: to pass '--issue-type' as a value, use '-- --issue-type'
Usage: atlassian-cli jira issue update --field <KEY=JSON_VALUE> <KEY>
```

`--issue-type` exists on `jira issue create` but not on `update`, so the two paths use different syntaxes for the same concept. More importantly, there is no supported way to *change* an issue's type in place — relevant because a Sub-task cannot be a child of an Epic (it must hang off a Story), so reparenting a Sub-task up to an Epic requires a type change. Today that means delete + recreate, losing the key, history, and comments.

**Note:** changing issue type is itself screen-/workflow-gated in many Jira projects (same class as Gap 8). Even with a `--issue-type` flag on update, the server may silently refuse — so this should land together with the Gap 8 silent-drop surfacing.

**Proposed fix:**
- Add `--issue-type <NAME>` to `jira issue update` (alias of `--field 'issuetype={"name":"..."}'`), consistent with `create`.
- Surface a structured warning if the type change is rejected by the project's edit screen (shared fix with Gap 8).

**Workaround today:** `--field 'issuetype={"name":"Story"}'` (when the screen allows it); otherwise delete + recreate and re-link manually.

---

## Gap 17 — Subcommand singular/plural & alias papercuts (extends Gap 6) 🔴

**Observed (2026-06-15 … 2026-06-24):** the CLI's subcommand names aren't consistently singular or plural, and common full-word forms have no alias. Each fails with a helpful tip, so impact is low — but collectively it's constant muscle-memory friction:

```
$ atlassian-cli jira issue transitions ...
error: unrecognized subcommand 'transitions'   tip: a similar subcommand exists: 'transition'
$ atlassian-cli bitbucket pullrequest ...
error: unrecognized subcommand 'pullrequest'    tip: a similar subcommand exists: 'pr'
$ atlassian-cli whoami
error: unrecognized subcommand 'whoami'          # only `bitbucket whoami` exists
```

Combined with Gap 6 (`comment` vs `comments`): `comments` is plural, `transition` is singular — no internal rule. `pr` has no `pullrequest` alias; there's no top-level `whoami`.

**Proposed fix:** add clap aliases so both forms work everywhere — `transition`/`transitions`, `comment`/`comments`, `pr`/`pullrequest` — and promote `whoami` to a top-level auth-validation command (wrapping the per-product identity call). Document one canonical form, accept the rest.

**Workaround today:** follow the `tip:` line the CLI prints; for identity use `atlassian-cli bitbucket whoami` or `auth test`.

---

## Gap 18 — Confluence page lookup gaps: `page list` fails on some spaces; no short-URL/URL resolution 🔴

**Observed (2026-07-07, profile `myorg`, space `TEAMSPACE`):**

```
$ atlassian-cli --profile myorg confluence page list --space TEAMSPACE
Error: Failed to list pages: Invalid response format: error decoding response body
```

**Same error string as the Jira 204 false alarm but this is a GET (read op), not a write.** A successful list GET returns 200 with a JSON body — not 204. So the `error decoding response body` here is a real failure, not the harmless empty-body quirk. The CLI cannot list pages in at least one Confluence space.

**Second failure — no URL-based page resolution:**

Confluence short links (`https://<instance>.atlassian.net/wiki/x/<HASH>`) and full page URLs cannot be passed to `confluence page get`. The command requires a bare numeric page ID as a positional:

```
$ atlassian-cli --profile myorg confluence page get "https://.../wiki/x/-wDioAE"
# error: invalid or missing page ID
```

There is no `--url` flag, no short-link resolution endpoint, and `--help` only documents `<PAGE_ID>`. When you have a link (from a browser, a Jira description, a Slack message) you must do a CQL search to discover the numeric ID before you can get the page.

**Workaround today:**
```bash
# 1. Search by title keywords to get numeric page ID
atlassian-cli --profile <p> confluence search cql "title ~ \"<keyword>\""

# 2. Use numeric ID to fetch page
atlassian-cli --profile <p> confluence page get <NUMERIC_PAGE_ID> --format json

# For page list failures, use search cql with a space filter instead:
atlassian-cli --profile <p> confluence search cql \
  "space.key = \"MYSPACE\" AND type = page" --limit 50
```

**Why it matters:**
- Confluence links are the canonical way people share pages (short links in Jira tickets, Slack, email). Every agent or script that processes such a link needs a multi-step CQL detour to get the content.
- `page list` failure makes it impossible to enumerate a space programmatically via the CLI — affects any tooling that audits space contents.

**Proposed fix:**
- Accept `--url <confluence-url>` on `confluence page get`: resolve via `GET /wiki/rest/api/content?spaceKey=...&title=...` or the v2 short-link resolver.
- Fix `confluence page list --space <KEY>` response format handling: the v2 Confluence REST API paginates differently from v1; the CLI likely calls the wrong endpoint or expects the wrong root key.

---

## Filing order suggestion

Group A — Confluence parity: Gaps 1, 2, 3, 4, 5, 18 → one issue titled
`[FEATURE] Confluence parity: inline comments, cross-space page move, accurate markdown export, page URL in create output, flag/positional consistency, URL-based page lookup, page list space filter`.

Group B — Trivial UX: Gap 6 → small standalone issue,
`[FEATURE] Add singular jira issue comment alias for comments`.

Group C — Bitbucket pipeline step control: Gap 7 → standalone,
`[FEATURE] Continue a Bitbucket pipeline past a manual step from the CLI`.

Group D — Jira write-path observability: Gap 8 → standalone,
`[FEATURE] Surface silently-dropped --field values (e.g. parent) on screen-gated Jira mutations`.

Group E — Jira read-path observability: Gap 9 → standalone,
`[FEATURE] Expose parent field in jira issue get output`.
(Filing-suggestion: link Gap 8 + Gap 9 in upstream issue bodies — same root concern, both directions of write-then-verify roundtrip.)

Group F — Jira resolution support: Gap 10 → standalone,
`[FEATURE] Expose resolution field in jira issue get output and add --resolution flag to transition/update`.
(Filing-suggestion: link Gap 9 + Gap 10 — both are missing fields in GET output; same underlying fix.)

Group G — Jira read-path field selection: Gaps 9 + 10 + 14 → fold into one issue,
`[FEATURE] Add --fields selection to jira issue get and search (incl. parent, resolution)`.
(Supersedes the standalone framing of E/F if the maintainer prefers a single read-path issue — all three are the same missing `fields` passthrough.)

Group H — Bitbucket CLI surface consistency: Gaps 11, 12, 13 → one issue,
`[FEATURE] Bitbucket parity: consistent --profile/--workspace/--repo handling, accept build-number on pipeline get, add pipeline step-log`.

Group I — Jira planning/agile surface: Gap 15 → standalone,
`[FEATURE] Add jira board/sprint listing and sprint-assignment commands`.

Group J — Jira issue mutation parity: Gap 16 → standalone,
`[FEATURE] Add --issue-type to jira issue update (in-place type change)`.
(Filing-suggestion: link Gap 8 + Gap 16 — both are screen-gated mutations needing silent-drop surfacing.)

Group K — Naming/alias papercuts: Gaps 6 + 17 → one trivial issue,
`[FEATURE] Add subcommand aliases (transition(s), comment(s), pr/pullrequest) and a top-level whoami`.

---

## Out of scope (cross-references only)

- Jira comment body truncation (~50 chars in `comments list`) — addressed by PR #64.
- Bitbucket Schedules listing — separate Bitbucket pipelines feature, not yet observed as blocking.
- Bitbucket `pr create --close-source-branch` — flag absent; weakly evidenced in transcripts (mostly discussed, not a hard error capture). Set as repo default in Bitbucket UI, or PATCH post-create via REST. Promote to a Gap if it recurs as a blocker.

---

## How to add a new entry

1. Observe the gap in real use; capture the exact command + error/output.
2. Append a new `## Gap N — <one-line title> 🔴` section above the "Filing order suggestion" section.
3. Include: **Observed**, **Why it matters** (when non-obvious), **Proposed fix**, **Workaround today**.
4. If multiple new entries fit a theme (e.g. all Bitbucket), update the filing-order section to group them.
5. When filed upstream, set the status emoji to 🟡 and add `Filed: <URL>`.
6. When resolved upstream, set 🟢 and add `Resolved in: <version/commit>`; remove the section in the next cleanup pass.
