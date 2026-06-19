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
$ atlassian-cli jira issue comment add SDAI-450 --body "..."
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

**Observed (2026-06-17, SDAI project on Centric8 Jira):**

```
$ atlassian-cli jira issue create \
    --project SDAI --issue-type "Story" \
    --summary "..." --description "..." \
    --field 'parent={"key":"SDAI-68"}'
INFO Issue created successfully key=SDAI-463
✅ Created issue: SDAI-463

$ atlassian-cli jira issue update SDAI-463 --field 'parent={"key":"SDAI-68"}'
ERROR Failed to parse JSON response: error decoding response body  # known 204 false alarm

# Verify
$ atlassian-cli jira issue search --jql "key = SDAI-463" -f json | jq '.[].parent'
null  # parent NEVER set — silently dropped on both create AND update
```

Subsequent JQL `parent = SDAI-68` confirms the issue is orphaned.

Root cause: the SDAI project's Story issue type doesn't have the `parent` field on its create/edit screen (workflow-configured restriction). Jira accepts the API call but ignores the `parent` value, returning success without setting it. The CLI relays the success and the caller has no signal that the linkage failed.

REST PUT directly to `/rest/api/3/issue/<KEY>` with `{"fields":{"parent":{"key":"..."}}}` also fails (`404` "Issue does not exist or you do not have permission to see it.") — the modern `parent` field is screen-permission-gated too.

**Why it matters:**
- Programmatic ticket creation cannot establish epic linkage without manual UI follow-up.
- Tickets are silently orphaned. Epic boards and "what's under X epic" reports miss them entirely until someone notices.
- No error signal at any layer — CLI exits 0, response body parses, status code is 2xx. Pure silent failure.
- Affects every cross-org Jira instance with workflow-restricted Story creation screens (common in mature setups).

**Proposed fix:**
- Issue-create response should surface the **persisted** parent value, not just the request. Emit `parent: SDAI-68` on success, `parent: null` if dropped — caller can fail-fast.
- If the create-screen config rejects a passed `--field`, surface a structured warning: `WARN '--field parent' silently dropped: Story type has no 'parent' field on the create screen for project SDAI.`
- Alternative: pre-check via `GET /rest/api/3/issue/createmeta?projectKeys=<P>&issuetypeNames=<T>&expand=projects.issuetypes.fields` before submitting; refuse the call if the supplied `--field` isn't in the meta.
- Companion `--strict-fields` flag for callers that want the call to **fail** rather than warn when a field is silently dropped.

**Workaround today:**
- After every programmatic create/update with `--field parent`, verify via JQL: `atlassian-cli jira issue search --jql "parent = <EPIC> AND key = <NEW_KEY>"`. Empty result = parent didn't stick → manual UI reparent.
- For known-affected projects, skip `--field 'parent='` at create time entirely; create first, then reparent via UI.

---

## Gap 9 — `jira issue get` output omits `parent` field even when set 🔴

**Observed (2026-06-18, SDAI project on Centric8 Jira):**

```
$ atlassian-cli jira issue create \
    --project SDAI --issue-type "Sub-task" \
    --summary "..." --description "..." \
    --field 'parent={"key":"SDAI-454"}'
INFO Issue created successfully key=SDAI-471
✅ Created issue: SDAI-471

# Verify parent linkage — GET shows no parent
$ atlassian-cli jira issue get SDAI-471 -f json | jq '.parent'
null

# But JQL confirms parent IS set correctly
$ atlassian-cli jira issue search --jql "parent = SDAI-454 AND key = SDAI-471"
SDAI-471 found ✓
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
atlassian-cli jira issue search --jql "key in (SDAI-470, SDAI-471, SDAI-473) AND parent = SDAI-454"
```

---

## Filing order suggestion

Group A — Confluence parity: Gaps 1, 2, 3, 4, 5 → one issue titled
`[FEATURE] Confluence parity: inline comments, cross-space page move, accurate markdown export, page URL in create output, flag/positional consistency`.

Group B — Trivial UX: Gap 6 → small standalone issue,
`[FEATURE] Add singular jira issue comment alias for comments`.

Group C — Bitbucket pipeline step control: Gap 7 → standalone,
`[FEATURE] Continue a Bitbucket pipeline past a manual step from the CLI`.

Group D — Jira write-path observability: Gap 8 → standalone,
`[FEATURE] Surface silently-dropped --field values (e.g. parent) on screen-gated Jira mutations`.

Group E — Jira read-path observability: Gap 9 → standalone,
`[FEATURE] Expose parent field in jira issue get output`.
(Filing-suggestion: link Gap 8 + Gap 9 in upstream issue bodies — same root concern, both directions of write-then-verify roundtrip.)

---

## Out of scope (cross-references only)

- Jira comment body truncation (~50 chars in `comments list`) — addressed by PR #64.
- Bitbucket Schedules listing — separate Bitbucket pipelines feature, not yet observed as blocking.
- Top-level `whoami` (currently only `bitbucket whoami`) — minor.

---

## How to add a new entry

1. Observe the gap in real use; capture the exact command + error/output.
2. Append a new `## Gap N — <one-line title> 🔴` section above the "Filing order suggestion" section.
3. Include: **Observed**, **Why it matters** (when non-obvious), **Proposed fix**, **Workaround today**.
4. If multiple new entries fit a theme (e.g. all Bitbucket), update the filing-order section to group them.
5. When filed upstream, set the status emoji to 🟡 and add `Filed: <URL>`.
6. When resolved upstream, set 🟢 and add `Resolved in: <version/commit>`; remove the section in the next cleanup pass.
