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

## Filing order suggestion

Group A — Confluence parity: Gaps 1, 2, 3, 4, 5 → one issue titled
`[FEATURE] Confluence parity: inline comments, cross-space page move, accurate markdown export, page URL in create output, flag/positional consistency`.

Group B — Trivial UX: Gap 6 → small standalone issue,
`[FEATURE] Add singular jira issue comment alias for comments`.

Group C — Bitbucket pipeline step control: Gap 7 → standalone,
`[FEATURE] Continue a Bitbucket pipeline past a manual step from the CLI`.

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
