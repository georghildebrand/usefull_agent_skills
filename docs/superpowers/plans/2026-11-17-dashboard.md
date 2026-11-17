# Dashboard Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A skill `/dashboard` that builds and refreshes private Artifact pages from a catalog of tiles and presets, with refresh buttons on the page and a confirmed write-back of ToDo marks.

**Architecture:** Python helper scripts turn source output (zotero2ai, session files, Jira, Confluence) into tile documents of a fixed shape. The session writes those documents into the page database with `ArtifactData`. One page template (HTML plus a pure `tiles.js`) renders every tile from its documents. Presets and every confidential value live in a private file outside the repo.

**Tech Stack:** Python 3 standard library only, `unittest`; plain JavaScript (no build step), tested with `node --test`; GridStack 10.3.1 from jsDelivr; Artifact capabilities `db`, `tts`, `comments`.

**Spec:** `docs/superpowers/specs/2026-11-17-dashboard-design.md` (read it first). Prototype: `docs/superpowers/specs/2026-11-17-dashboard-prototype/prototype-page.html`.

## Global Constraints

- Everything lives in `skills/dashboard/`. Tests: `skills/dashboard/tests/`, run as `python3 skills/dashboard/tests/<file>.py` and `node --test skills/dashboard/tests/`.
- Python: standard library only. JavaScript: no npm packages.
- No confidential value in the repo: no customer names, no internal Jira project keys or Confluence space keys, no artifact URLs, no company hostnames, no people's names. Test fixtures are hand-written and synthetic. No test reads `~/.claude` or calls a real API.
- Private file: `~/.config/claude-dashboard/presets.json`. Scripts take its path as an argument, default `~/.config/claude-dashboard/presets.json`.
- Every tile document has `v: 1`, `syncedAt` (ISO 8601 UTC, `Z` suffix) and `source`. At most 256 KiB serialized.
- Page copy is German, as in the prototype. Code, file names, document fields are English.
- Every tile shows "Stand: <syncedAt>" and has a refresh button.
- Refresh comment text, exactly: `dashboard refresh <preset> <tile|all>`. Sync: `dashboard sync <preset>`.
- Writes to a source system (zotero2ai) happen only in `/dashboard sync`, only after the user says yes in the session.
- Commits: one per task, message starts with `dashboard:`.

## Review Focus

- A tile whose document is missing or empty must show a designed empty state, never a blank tile or a script error.
- A ToDo whose status changed in zotero2ai after the user marked it must be listed as "changed in source" and skipped, never overwritten.
- A source with more rows than fit in 256 KiB (for example 400 ToDos with long titles) must be trimmed with a visible count, never rejected by the database.
- A comment on the page that is free text, or names an unknown preset or tile, must be ignored by the refresh handler, never trigger a refresh.
- A session file or source row with missing fields (format changes in Claude Code, Jira issue without priority) must be skipped or filled with empty strings, never crash the script.

---

### Task 1: Document helpers and the ToDo builder

**Files:**
- Create: `skills/dashboard/scripts/common.py`
- Create: `skills/dashboard/scripts/build_todos.py`
- Create: `skills/dashboard/tests/fixtures/todo_list_small.json` (synthetic, 5 ToDos: statuses `todo`, `in_progress`, `blocked`, `done`, `cancelled`; one title with the `[MEM][todo][x] ` prefix)
- Test: `skills/dashboard/tests/test_build_todos.py`

**Interfaces:**
- Produces: `common.now_iso() -> str`; `common.envelope(source: str, items: list, **extra) -> dict` returning `{"v": 1, "syncedAt": ..., "source": ..., "items": items, **extra}`; `common.fit_document(doc: dict, limit: int = 262144) -> dict` that drops items from the end until the JSON is under the limit and sets `truncated: <dropped count>`; `common.write_json(path, doc)`.
- Produces: `build_todos.build(todo_list_result: dict, project: str) -> dict`. Input is the parsed `result` string of zotero2ai `todo_list`. Output items: `{key, title, status, priority, version, updatedAt, createdAt, order}`, only statuses `todo`, `in_progress`, `blocked`, title prefix `[MEM][todo][...] ` removed, cut to 220 characters, sorted by `updatedAt` descending. Extra field `project`. CLI: `build_todos.py <tool-result-file> <project> <out.json>`; the tool-result file is the saved MCP output `{"result": "<json string>"}`.

- [ ] **Step 1:** Write tests: `test_open_statuses_only` (5 in, 3 out); `test_prefix_removed`; `test_sorted_by_updated_desc`; `test_fit_document_trims` (600 items with 1 KiB titles → under 262144 bytes, `truncated` > 0, first item kept); `test_envelope_fields` (`v == 1`, `syncedAt` ends with `Z`).
- [ ] **Step 2:** Run `python3 skills/dashboard/tests/test_build_todos.py`. Expected: FAIL (import error).
- [ ] **Step 3:** Implement `common.py` and `build_todos.py` with the signatures above.
- [ ] **Step 4:** Run the test. Expected: OK, 5 tests.
- [ ] **Step 5:** Commit `dashboard: add document helpers and ToDo builder`.

### Task 2: Session and Jira builders

**Files:**
- Create: `skills/dashboard/scripts/build_sessions.py`, `skills/dashboard/scripts/build_jira.py`
- Create: `skills/dashboard/tests/fixtures/sessions/` (3 synthetic `<pid>.json` files; one without `name` and `kind`), `skills/dashboard/tests/fixtures/projects/p1/<sessionId>.jsonl` (empty file for one session), `skills/dashboard/tests/fixtures/jira_search.json` (REST `/rest/api/3/search/jql` shape, 4 issues; one with `priority: null`)
- Test: `skills/dashboard/tests/test_build_sources.py`

**Interfaces:**
- Consumes: `common.envelope`, `common.fit_document`.
- Produces: `build_sessions.build(sessions_dir: str, projects_dir: str, home: str) -> dict`. Items `{name, kind, state, startedAt, lastActiveAt, cwd, hasTranscript}`; `name` falls back to the first 8 characters of `sessionId`; `cwd` has `home` replaced by `~`; `lastActiveAt` = newest of transcript mtime, `statusUpdatedAt`, `updatedAt`. Extra field `updatedAt`. CLI: `build_sessions.py <out.json>` with real paths.
- Produces: `build_jira.build(issues: list, my_account_id: str, base_url: str) -> dict`. Items `{key, title, project, type, status, statusCat, priority, updatedAt, createdAt, role, parent, order}`; `role` is `assignee`, `reporter` or `other`; missing fields become `""`. Extra fields `baseUrl`, `scope`. Fetching stays in the tile recipe (Task 6), not in this script.

- [ ] **Step 1:** Write tests: `test_session_missing_fields_fall_back`; `test_session_last_active_uses_transcript`; `test_session_home_replaced`; `test_jira_null_priority_is_empty`; `test_jira_role`.
- [ ] **Step 2:** Run `python3 skills/dashboard/tests/test_build_sources.py`. Expected: FAIL.
- [ ] **Step 3:** Implement both builders.
- [ ] **Step 4:** Run the test. Expected: OK, 5 tests.
- [ ] **Step 5:** Commit `dashboard: add session and Jira builders`.

### Task 3: Newsfeed builder and sync planner

**Files:**
- Create: `skills/dashboard/scripts/build_feed.py`, `skills/dashboard/scripts/plan_sync.py`
- Create: fixtures `confluence_cql.json` (3 pages, one already in the feed), `feed_existing.json`, `flags.json`, `notes.json`, `todo_list_now.json`
- Test: `skills/dashboard/tests/test_feed_and_sync.py`

**Interfaces:**
- Produces: `build_feed.merge(existing: dict | None, new_items: list, now: str, keep_days: int = 30) -> dict`. Items `{id, kind, title, link, source, changedAt, why}` where `id` is `"<source>:<native id>:<changedAt>"`, `why` is `"changed"`, `"mention"` or `"watching"`. New items first, duplicates by `id` dropped, items older than `keep_days` dropped. `build_feed.markers(existing_markers: dict | None, source: str, now: str) -> dict`. `build_feed.since(markers: dict | None, source: str, now: str) -> str` returns the stored marker or `now` minus 7 days.
- Produces: `plan_sync.plan(flags: dict, notes: dict, current_todos: list, seen: dict) -> list[dict]`. `seen` is `{key: status_at_mark_time}` from the page's `todostate/seen` document (never from `todolists/*`, which a refresh rewrites with the current source status). Each row `{key, title, from, to, note, action}` with `action` one of `transition`, `changed_in_source`, `needs_reason` (target `blocked` without note), `unknown_key`. Non-string flag values, values that are not one of the five ToDo statuses (for example `""`), and keys `createdAt` are ignored.

- [ ] **Step 1:** Write tests: `test_feed_dedup_and_order`; `test_feed_drops_old`; `test_since_defaults_to_7_days`; `test_plan_changed_in_source` (mark set on status `todo`, source now `in_progress` → `changed_in_source`); `test_plan_blocked_needs_reason`; `test_plan_ignores_meta_keys`.
- [ ] **Step 2:** Run `python3 skills/dashboard/tests/test_feed_and_sync.py`. Expected: FAIL.
- [ ] **Step 3:** Implement both modules.
- [ ] **Step 4:** Run the test. Expected: OK, 6 tests.
- [ ] **Step 5:** Commit `dashboard: add newsfeed builder and sync planner`.

### Task 4: Presets and the confidentiality check

**Files:**
- Create: `skills/dashboard/scripts/presets.py`, `skills/dashboard/scripts/check-clean.sh`, `skills/dashboard/presets/global.json`
- Create: fixture `private_presets.json` (synthetic values, for example Jira key `ACME`, URL `https://claude.ai/artifact/TESTONLY`)
- Test: `skills/dashboard/tests/test_presets.py`

**Interfaces:**
- Produces: `presets.load(name: str, repo_dir: str, private_path: str) -> dict`. Merge order: repo preset, then private preset of the same name; a preset only in the private file is allowed. Result keys: `name`, `url` (`None` when not set), `tiles` (list of `{kind, x, y, w, h}`), `filters` (dict), `sources` (dict). Raises `KeyError` with the preset name when neither file has it.
- Produces: `presets.set_url(name: str, url: str, private_path: str) -> None`, creates the file and the parent folder when missing.
- Produces: `presets.add_tile(name: str, kind: str, private_path: str, w: int = 6, h: int = 4, skill_id: str | None = None) -> dict`: appends `{kind, x: 0, y: <below the lowest tile>, w, h}` to the private preset (creating the preset entry when missing) and returns the updated preset. For `kind == "list"` the tile also gets `id: "list:<skill_id>"`, the id the page needs to find `lists/<skill_id>`. Raises `ValueError` for a `kind` not in `TILE_KINDS = ["todos", "jira", "sessions", "status", "statustable", "feed", "list", "note"]`, for a list tile without a `skill_id` that is one database path segment (same rule as `SEGMENT` in `tiles.js`), for a list that is already in the preset, and for a `skill_id` given with another kind. `/dashboard add <preset> list:<skill-id>` calls `add_tile(preset, "list", ..., skill_id=<skill-id>)`.
- Produces: `presets.secret_values(private_path: str) -> list[str]`: every string value in the private file (URLs, keys, names) plus its `denyList` array, deduplicated, strings shorter than 3 characters left out.
- Produces: `check-clean.sh [private_path]`: runs `grep -rniF` for every value from `secret_values` over `skills/dashboard` and the two spec/plan files. Exit 1 and print `file:line` (not the value) on a hit. Exit 0 and print `clean` otherwise. Prints `no private file, nothing to check` and exits 0 when the file is missing.
- `presets/global.json`: tiles `todos`, `jira`, `sessions`, `status`, `statustable`, `feed`; no `url`; `sources` with placeholder strings only (`"<jira project keys>"`).

- [ ] **Step 1:** Write tests: `test_private_overrides_repo`; `test_private_only_preset`; `test_unknown_preset_raises`; `test_url_none_when_missing`; `test_set_url_creates_file`; `test_add_tile_below_lowest`; `test_add_tile_unknown_kind_raises`; `test_add_tile_list_writes_list_id`; `test_add_tile_list_needs_valid_skill_id`; `test_check_clean_finds_value` (temp dir with a file containing `ACME` → exit 1, output has no `ACME`).
- [ ] **Step 2:** Run `python3 skills/dashboard/tests/test_presets.py`. Expected: FAIL.
- [ ] **Step 3:** Implement `presets.py`, `check-clean.sh`, `global.json`.
- [ ] **Step 4:** Run the test. Expected: OK, 8 tests.
- [ ] **Step 5:** Commit `dashboard: add presets and confidentiality check`.

### Task 5: Page template

**Files:**
- Create: `skills/dashboard/template/page.html` (from the prototype), `skills/dashboard/template/tiles.js`
- Test: `skills/dashboard/tests/tiles.test.js`

**Interfaces:**
- Consumes: the document shapes of Tasks 1 to 4.
- Produces in `tiles.js` (pure functions, no DOM, exported with `if (typeof module !== 'undefined') module.exports = {...}` and as `window.DashTiles` in the page): `filterTodos(lists, flt, now)`, `filterJira(doc, flt, now)`, `sortSessions(items, flt)`, `filterFeed(doc, read, flt)`, `validateList(doc) -> {ok: boolean, reason?: string}`, `parseCommand(text) -> {cmd: 'refresh'|'sync', preset, tile} | null`, `emptyText(kind, state) -> string`, and the constant `TILE_KINDS` with the same values as in `presets.py`. `parseCommand` accepts a tile only from `TILE_KINDS` or `all`; a `list` tile is addressed as `list:<skill-id>`. The filter objects use the prototype's field names (`q`, `project`, `status`, `prio`, `age`, `jq`, `jproject`, `jrole`, `jstat`, `jtype`, `jage`, `sq`, `ssort`).
- Produces in `page.html`: the page reads `<meta name="dashboard-preset" content="...">` and `<meta name="dashboard-template" content="1">`. Template placeholders the skill replaces at publish: `__PRESET__`, `__TITLE__`, and `__LAYOUT__` inside `<script type="application/json" id="dashboard-layout">`, replaced by the JSON array of the preset's `tiles` (with `<` written as `\u003c`). `tiles.presetLayout(tiles) -> {items, skipped}` turns it into the start layout (id = the tile's `id`, else its kind, repeats numbered `kind-2`; a `list` tile must carry `id: "list:<skill-id>"`, which `presets.add_tile` writes). A malformed tile (unknown kind, list tile without a valid id, missing size, repeated id) is left out and counted in `skipped`; the other tiles stay. The page shows that start layout while `meta/layout` does not exist and after "Anordnung zurücksetzen", and its status line says how many preset tiles were left out. The hard-coded global tiles are only the fallback when `__LAYOUT__` is not filled in, or when no preset tile is usable (then the status line says so). Database documents read: those of the spec, plus `meta/layout` (`{items: [{id, kind, x, y, w, h}]}`, written by the page on layout change, one write per change after 1 s without further change) and `todostate/seen` (`{key: status shown when the mark was set}`, written by the page in the same step as `todostate/flags`). Taking a mark back removes the key from `todostate/flags`, `todostate/seen` and `todostate/notes`. A mark whose `seen` status differs from the current status shows a hint and a "bestätigen" button. Every tile whose document has `truncated > 0` says in its caption how many rows the size limit left out.
- Changes against the prototype, nothing else: demo tiles `statA`, `statB`, `spark`, `bars` removed; tiles `statustable`, `feed`, `list` added; the "Widget hinzufügen" drop-down lists the fixed kinds plus one entry per document in the `lists` collection (label = its `title`); layout moves from `localStorage` to `meta/layout` (filters stay in `localStorage`); a refresh button in every tile header and one in the page header; `capabilities` grow by `comments` (full form, for `sendToClaude`). Refresh click: `canSendToClaude()`; `"available"` → `sendToClaude({anchor: await anchorFor(tileElement), text: 'dashboard refresh <preset> <tile>'})` and the tile shows "Auffrischen angefordert um <HH:MM>"; anything else → the tile shows the command `/dashboard refresh <preset> <tile>` with a copy button.

- [ ] **Step 1:** Write tests in `tiles.test.js`: `parseCommand('dashboard refresh global jira')` returns `{cmd:'refresh', preset:'global', tile:'jira'}`; `parseCommand('bitte auffrischen')` returns `null`; `parseCommand('dashboard refresh global nonsense')` returns `null` (unknown tile); `validateList({v:2})` is not ok; `validateList` on 600 items is ok and the page shows the first 500; `filterTodos` with `age: '60'` drops an item changed 61 days before `now`; `emptyText('jira','empty')` is non-empty.
- [ ] **Step 2:** Run `node --test skills/dashboard/tests/`. Expected: FAIL.
- [ ] **Step 3:** Write `tiles.js`, then build `page.html` from the prototype using it.
- [ ] **Step 4:** Run `node --test skills/dashboard/tests/` (expected: all pass) and `node --check` on the inline script of `page.html` (expected: no output).
- [ ] **Step 5:** Commit `dashboard: add page template and tile functions`.

### Task 6: Skill file and tile recipes

**Files:**
- Create: `skills/dashboard/SKILL.md`, `skills/dashboard/tiles/{todos,sessions,status,jira,statustable,feed,list}.md`
- Modify: `README.md` (one line in the skill list)

**Interfaces:**
- Consumes: every script and the template.
- `SKILL.md` covers, in this order: when to use (`/dashboard`, "Übersicht", "Einstiegspunkt für <Projekt>"); the four commands from the spec with their exact steps; publishing (`Artifact` publish with `files: {"tiles.js": ...}`, capabilities `{db: {rules: [{path: "", read: "view", write: "admin"}]}, tts: {}, comments: {}}`, then `presets.set_url`; before the publish, replace `__PRESET__`, `__TITLE__` and `__LAYOUT__` (the JSON of the preset's `tiles`, `<` as `\u003c`); a republish never writes `meta/layout`); answering a refresh comment (only `parseCommand` matches, reply in one line, resolve the thread; do nothing when a newer Claude reply exists); `/dashboard sync` (run `plan_sync` with `seen` read from `todostate/seen`, show the table, write after yes, `blocked` uses the note as reason, other notes via `create_or_extend_note` on the ToDo item, then remove written marks from `todostate/flags`, `todostate/seen` and `todostate/notes`); confidentiality (run `check-clean.sh` before every commit; titles of ToDos and tickets go only into the page database, never into the repo).
- Each `tiles/<id>.md`: source command (exact tool or CLI call with placeholders from `sources`), how its output is saved to a file, which builder turns it into which document, what is left out. `feed.md` uses the CQL and JQL from spec item 7. `statustable.md`: the dashboard session converts the rows of the `statustable` skill into a `statustable/current` document; the `statustable` skill itself is not changed.

- [ ] **Step 1:** Write `SKILL.md` and the seven recipes.
- [ ] **Step 2:** Run `bash skills/dashboard/scripts/check-clean.sh`. Expected: `clean`.
- [ ] **Step 3:** Commit `dashboard: add skill and tile recipes`.

### Task 7: Acceptance on a test page, then the global preset

**Files:**
- Modify: none in the repo, unless a check fails (then fix in the owning task's files).

- [ ] **Step 1:** Publish a private test artifact from the template with preset name `test` and fake documents built from the test fixtures. Checks: every tile renders with data; delete one document per tile and every tile shows its empty text; every tile shows "Stand"; with this session watching, a tile's refresh button posts `dashboard refresh test <tile>` and this session receives it; after stopping the watch (`ArtifactComments` `watch` `on: false`), the button shows the command instead.
- [ ] **Step 2:** Open the test page once in a desktop browser and once in the Code tab's Artifacts pane. Expected: no overflow, both themes readable, speech button present only in the browser.
- [ ] **Step 3:** Run `/dashboard sync test` on fake marks. Expected: the table is shown, nothing is written before a yes.
- [ ] **Step 4:** Ask the user to put the prototype's URL into the private file for preset `global` (or set it with `presets.set_url` after the user names it). Run `/dashboard global`. Expected: the page is republished from the template, the ToDo, session, status and Jira tiles keep their data, the new tiles show their empty text until the first refresh.
- [ ] **Step 5:** Run all tests and `check-clean.sh`. Expected: all pass, `clean`. Commit any fixes with `dashboard: fixes from acceptance`.
