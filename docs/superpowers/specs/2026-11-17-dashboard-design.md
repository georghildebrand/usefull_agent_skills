# Dashboard skill: a catalog of tiles, assembled into private pages on demand

Status: draft for review, 2026-11-17.

## Intent

The user works in several projects at once. Some pages are needed for one project
(a customer project, an observability tool, an API gateway). Other pages give a global
view: which Claude Code sessions are running, which ToDos are open, which tickets
wait. Today every such page is built by hand in a session and is lost or goes stale
afterwards.

The skill keeps a **catalog of tiles** the user uses often. On a short command it
assembles a **private page (Artifact)** from a **preset**, fills each tile with fresh
data, and keeps the page at a fixed address. The user can add more tiles from a
drop-down on the page. A refresh is on demand: one button for all tiles, one button
per tile.

A working prototype exists: the Artifact "Widget-Raster", built on 2026-11-17 in one
session. It has the grid, the tiles for ToDos, sessions, status-to-listen, Jira
tickets, write-back marks with notes, filters, and a database per page. The skill
turns that prototype into a reusable template.

## Goals

- `/dashboard <preset>` builds the page for a preset, or refreshes it if it exists.
- `/dashboard refresh <preset> [tile]` refreshes all tiles or one tile.
- `/dashboard sync <preset>` carries marks the user set on the page (for example "→
  cancelled" on a ToDo, with a note) back into the source system, after the user
  confirms the list in the session.
- A tile catalog. Each tile is defined once and used by every preset.
- Presets: one global preset in the repo as an example; project presets in a private
  file on the user's machine.
- Refresh buttons on the page: one in the page header ("all tiles"), one in each tile
  header ("this tile").
- A new skill can offer a tile without new page code, through a generic list tile
  (see "Generic list tile").

## Non-goals (first version)

- Live data without a session. The page cannot reach local data on its own (see
  Constraints). Approach C below is a later experiment for single tiles.
- Push notifications. The newsfeed tile marks new entries on the page; it does not
  alert the user anywhere else.
- Scheduled refresh. Refresh happens when the user asks.
- Writing to Jira, Confluence or Bitbucket from the page. Jira and Confluence tiles
  are read-only. Only the ToDo tile writes back, and only through `/dashboard sync`
  with a confirmation in the session.

## Anti-goals (would make it a failure even if it works)

- A page shows data as current that is hours old without saying so. Every tile shows
  "Stand: <time>" of its last fill.
- A click on the page changes a source system (zotero2ai, Jira) without the user
  seeing the list of changes in a session first.
- Confidential names (customers, internal project keys, artifact addresses, people)
  end up in the shared skill repo.
- The catalog becomes a copy-paste collection: the same tile code exists twice.

## Constraints

- **Artifact sandbox.** The page cannot fetch from other hosts. All data comes from
  the page's own database (`db` capability), written by a Claude session with the
  `ArtifactData` tool.
- **A page cannot start a session.** It can send a comment to Claude with
  `comments.sendToClaude({anchor, text})` (editors only). The platform notifies the
  sessions that watch the artifact. `comments.canSendToClaude()` returns
  `"no_session"` when nobody listens. Then the page shows the command to type instead.
- **Watching is per session.** A session watches an artifact after it publishes it,
  or after `ArtifactComments` `watch`. A read alone does not start a watch. Watches
  end with the session.
- **Shared repo.** The skill lives in `usefull_agent_skills`, which is shared. Rules
  from the `skill-confidentiality-boundary` skill apply: no customer names, no
  internal Jira project keys or Confluence space keys, no artifact URLs, no people's
  names in the repo. These go into the private preset file.
- **Database limits.** At most 256 KiB per document and 25,000 documents per page.
  A tile writes one document per source (one per ToDo project, one for Jira), not one
  document per row.
- **Text to speech** works only in Chrome or Edge in the browser and not in the mobile
  apps or the Code tab's Artifacts pane. The status tile shows the text in every view.

## Approaches

The user chose **A** on 2026-11-17.

- **A. Skill with catalog (chosen).** A skill holds the page template, the tile
  catalog with a fill recipe per tile, and presets. A session fills the page. The
  refresh button sends a comment to Claude; without a watching session the user types
  `/dashboard refresh <preset>`. Trade-off: every refresh needs a running session.
- **B. A plus one background session that watches all dashboards.** Buttons work
  without the user doing anything. Trade-off: background sessions end when the Mac
  sleeps and must be restarted. Can be added to A later without changing A.
- **C. Tiles call local MCP servers directly** (`mcp` capability with `host:` servers).
  Live data for tiles whose source is an MCP server (for example the ToDo tile and
  zotero2ai), no session needed. Trade-off: works only in the Claude desktop app, and
  not for sources without an MCP server (the session list). Not tested. Later
  experiment on one tile.

## Design

### Skill layout

```
skills/dashboard/
  SKILL.md                 commands, flow, rules (confirmation, confidentiality)
  template/page.html       the page: grid, tile runtime, all tile renderers
  tiles/<tile-id>.md       one fill recipe per tile (see Tile contract)
  presets/global.json      example preset, no confidential values
  scripts/                 helpers that turn source output into tile documents
```

Private, outside the repo: `~/.config/claude-dashboard/presets.json`. It holds, per
preset: the artifact URL, the tiles with size and position, default filter values,
and source settings (Jira project keys, Confluence space keys, ToDo projects).
The skill reads this file first. A preset only in the repo has no URL yet; the
first `/dashboard <preset>` publishes the page and writes the URL into the private
file.

### Tile contract

Each tile has:

- **id and title**, for example `todos`, "Aufgaben".
- **Data documents** in the page database, with a fixed schema. Every document has
  `syncedAt` (ISO time) and `source` (a short label).
- **A fill recipe** in `tiles/<id>.md`: which tool or command reads the source, how
  the output becomes the document, what is left out (for example ToDo descriptions).
  Large source output goes to a file and is turned into the document by a script, so
  rows never pass through the conversation.
- **A renderer** in `template/page.html`: reads only its documents, renders a filter
  bar once and the list below it, shows "Stand: <syncedAt>".
- **Write-back (optional):** documents the page writes (marks, notes), and a sync
  recipe that reads them, shows the list to the user, and writes after a yes.

### Tiles in the first version

| Tile | Source | Data documents | Writes back |
|---|---|---|---|
| ToDos | zotero2ai `todo_list` per project | `todolists/<project>`; page writes `todostate/flags`, `todostate/seen` (status at mark time), `todostate/notes` | yes, through `/dashboard sync` (`todo_transition`) |
| Sessions | `~/.claude/sessions/*.json` plus transcript change time | `sessions/list` | no |
| Status to listen | text written by the session | `status/<id>`, menu over all | no |
| Jira tickets | Jira REST search, assignee or reporter, open, project keys from the preset | `jira/open` | no |
| Status table | the `statustable` skill writes its rows | `statustable/current` | no |
| Newsfeed | Confluence (pages changed in the preset's spaces, mentions of the user) and Jira (status changes, mentions) since a stored marker | `feed/items`, `feed/markers`; page writes `feed/read` | no |
| Generic list | any skill | `lists/<skill-id>` | no |

The demo tiles of the prototype (sample chart, sample bars, sample numbers, free note)
are dropped. The free note can stay as a tile without a source.

### Generic list tile

Answers the idea "one widget per skill". A skill writes one document in a fixed
shape: `{title, syncedAt, source, items: [{title, link?, status?, date?, group?}]}`.
The tile shows any such document with search, a status filter and a date sort. The
drop-down "Widget hinzufügen" lists every `lists/*` document it finds. A skill that
wants a tile only needs to write that document; the skill's own SKILL.md says how.

### Refresh

- Each tile header and the page header get a button "Auffrischen".
- On click the page calls `canSendToClaude()`.
  - `available`: `sendToClaude({anchor: <tile or header>, text: "dashboard refresh <preset> <tile|all>"})`.
    The tile shows "Auffrischen angefordert um <time>".
  - `no_session` or anything else: the tile shows the command
    `/dashboard refresh <preset> <tile>` as selectable text with a copy button.
- The session that receives the comment runs the fill recipe of that tile (or all),
  writes the documents, replies in the thread with one line, and resolves it.

### Commands

- `/dashboard <preset>`: if the private file has a URL, read the artifact, compare the
  page template version, republish if the template is newer, then refresh all tiles.
  Without URL: publish from the template, store the URL, fill all tiles.
- `/dashboard refresh <preset> [tile]`: run fill recipes only. No republish.
- `/dashboard sync <preset>`: read write-back documents, show a table of planned
  changes, write after the user says yes, clear the marks that were written, refresh
  the tile.
- `/dashboard add <preset> <tile>`: add a tile to the preset in the private file and
  to the page. A list tile is named `list:<skill-id>`; the preset stores it with that id.

### The existing prototype

The Artifact "Widget-Raster" becomes the page of the `global` preset. Its URL goes into
the private file. Its database already holds the documents of the first four tiles in
the schema above. The first `/dashboard global` republishes it from the template.

### Sources set on 2026-11-17

- Jira: only the project of the user's current team.
- Confluence: only the space of the user's current team.
- Bitbucket: not named yet; the newsfeed starts without it.
- The concrete keys live only in the private preset file.

## Details settled after the builder check

Items marked *(call)* were decided by the agent that wrote this spec, not by the
user. The user can overrule them.

1. **Prototype source.** A copy of the prototype page is in
   `2026-11-17-dashboard-prototype/prototype-page.html` next to this spec. The
   company Jira address that was its fallback is removed; the base URL comes only
   from the data document. The live page's database was checked with `ArtifactData`
   `list`/`get` during the build: it holds `todolists/<project>`, `todostate/flags`,
   `todostate/notes`, `sessions/list`, `status/<id>` and `jira/open` in the shapes
   listed above. The template starts from this file. It is not a rewrite.
2. **Who answers a refresh comment.** *(call)* The normal case is the session in
   which the user runs `/dashboard`: publishing the page, or `ArtifactComments`
   `watch` when there is no republish, makes that session watch it. The fallback is the typed command. No long-running dashboard
   session in v1 (that is approach B). The handler accepts only the exact text
   `dashboard refresh <preset> <tile|all>` and `dashboard sync <preset>`. Sync from a
   comment only lists the planned changes in the reply; it writes only after a yes
   in the session. If two sessions watch: a session that finds a Claude reply newer
   than the request in the thread does nothing.
3. **Confidentiality check.** *(call)* Two layers. A script `scripts/check-clean.sh`
   greps the skill folder for every value in the private preset file (keys, space
   keys, URLs, names) and for a private deny list in the same file. It must pass
   before every commit. Then a manual review using the `skill-confidentiality-boundary`
   skill. German labels and field names are not confidential.
4. **Session source format.** Each `~/.claude/sessions/<pid>.json` has `sessionId`,
   `name`, `kind` (`interactive` or `bg`), `status` (`idle` or `busy`), `cwd`,
   `startedAt` (epoch ms), `updatedAt`, `statusUpdatedAt`. The transcript is
   `~/.claude/projects/*/<sessionId>.jsonl`; "last active" is the newest of its
   modification time and `statusUpdatedAt`. The tile shows `status` as it is; it
   does not decide "running" itself. The format is not documented by Claude Code and
   can change: the script must skip fields it does not find.
5. **Status-to-listen text.** The session writes `status/<id>` with `title`, `order`,
   `text`, `updatedAt`. `/dashboard refresh <preset> status` writes `status/current`
   from the state of the session that runs it. Speech uses the `tts` capability as in
   the prototype.
6. **Sync mapping for ToDos.** A flag value is the target status (`in_progress`,
   `done`, `blocked`, `cancelled`, `todo`) and maps 1:1 to `todo_transition`.
   `blocked` needs a reason: the note is used; with no note the sync asks for one.
   *(call)* Other notes go as a child note on the ToDo's Zotero item
   (`create_or_extend_note`), because `todo_transition` has no note field. Before
   writing, the sync reads the current `version` of each ToDo. If the status changed
   since the mark was set, that row is shown as "changed in source" and skipped. After
   a successful write the mark and note are removed from the page.
7. **Newsfeed.** *(call)* The marker is the time of the last successful fetch per
   source in `feed/markers`. A first run without marker fetches the last 7 days.
   Confluence: CQL `space in (<spaces>) and lastmodified >= <marker>`, plus
   `mention = currentUser()`. Jira: `project in (<keys>) and updated >= <marker>`, plus
   `watcher = currentUser()`. CLI profile from the private file. The page writes
   `feed/read` (`{<item id>: true}`); the session never writes it and drops ids of
   items older than 30 days.
8. **Layout.** *(call)* The preset gives the layout for the first build only. After
   that the page keeps the layout in its database (`meta/layout`), so it is the same
   on every device. A tile added on the page does not change the preset;
   `/dashboard add` changes both. A republish never changes `meta/layout`.
9. **Generic list limits.** *(call)* Documents carry `v: 1`. At most 500 items; the
   tile shows the first 500 and says so. A malformed document shows "Diese Liste hat
   ein unbekanntes Format" with the document name.
10. **First run on the prototype.** The database survives a republish: the prototype
    was republished six times after its database was created (versions 3 to 8), and
    the data stayed intact each time. Artifacts keep
    a version history, so no extra backup. The URL of the prototype is put into the
    private file by hand at setup.
11. **Acceptance.** *(call)* The builder may publish one private test artifact with
    fake data. Done means: every tile renders with data and with an empty database,
    shows "Stand", and has a refresh button. The refresh button posts a comment when a
    session watches, and shows the command when no session watches. `/dashboard sync`
    shows the table and writes nothing without a yes. `check-clean.sh` passes.
    Checked once in a desktop browser and once in the Code tab's Artifacts pane.

## Left to the builder

- How the template version is stored and compared (for example a `<meta>` tag and a
  `meta/template` document).
- Exact filter controls per tile beyond those in the prototype.
- Layout of the page header and the drop-down.
- Script language for the helpers (the prototype used Python with only the standard
  library).
