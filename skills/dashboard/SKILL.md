---
name: dashboard
description: Use when the user types /dashboard, asks for an "Übersicht", or asks for an "Einstiegspunkt für <Projekt>". Builds or refreshes a private page (Artifact) from a preset of tiles such as ToDos, sessions, Jira tickets, status table and newsfeed.
---

# Dashboard

A dashboard is a private page (Artifact) made of tiles. Each tile shows one
document from the page's own database. This skill fills those documents and
keeps the page at one address.

## Files

- `template/page.html` and `template/tiles.js`: the page. Do not edit per preset.
- `tiles/<id>.md`: one recipe per tile. It says how to fill the tile.
- `presets/global.json`: example preset without private values.
- `scripts/`: Python helpers (standard library only). They turn source output into documents.
- Private file: `~/.config/claude-dashboard/presets.json`. It holds the page URL, tiles, filters and sources (project keys, space keys) per preset. It is never copied into the repo.

`<skill dir>` in this file and in the tile recipes is the base directory that the
Skill tool reports for this skill (the folder that holds this SKILL.md). Write it as
an absolute path in every command. Then the commands work from any working
directory and from an installed copy.

Load a preset in Python:

```
python3 -I -c "import sys,json; sys.path.insert(0,'<skill dir>/scripts'); import presets; print(json.dumps(presets.load('<preset>', '<skill dir>')))"
```

## Documents

Every tile document has `v: 1`, `syncedAt` (ISO 8601 UTC, Z suffix) and `source`.
A document is at most 256 KiB. The builders enforce this. Large source output goes
to a file in the scratchpad first. A script turns the file into the document, so rows
never pass through the conversation.

Write a document with `ArtifactData` `set` (or `batch` for several). Always pass
`if_version` from your last read of that document. On a version conflict, read it
again and decide. Do not overwrite blindly.

## Commands

### /dashboard <preset>

1. Load the preset (see above). Unknown name: stop and say so.
2. No URL yet: publish (see Publishing), then store the URL.
3. URL exists: read the artifact with `Artifact` `action: read`. If `<meta name="dashboard-template">` in the live page is older than the one in `template/page.html`, republish. A read does not make the session watch the page. When there is no republish, call `ArtifactComments` `action: watch` with the URL, so the refresh buttons reach this session. Check that the result says auto-replies are armed. If they are not armed, tell the user that the refresh buttons will show the command to type instead.
4. Run every tile recipe of the preset (refresh all).
5. Reply with one line per tile: filled, or why not.

### /dashboard refresh <preset> [tile]

Run only the fill recipes: all tiles, or the one named. A list tile is `list:<skill-id>`. No republish.

### /dashboard sync <preset>

Writes marks from the page back to the ToDo source. Only the ToDo tile does this.

1. Read `todostate/flags`, `todostate/seen` and `todostate/notes` from the page database.
2. Read the current ToDos with `todo_list` for each project in `sources.todos`.
3. Run `plan_sync.plan(flags, notes, current_todos, seen)`. Take `seen` from `todostate/seen`. Never take it from `todolists/*`: a refresh rewrites those with the current status.
4. Show the rows as a table: key, title, from, to, note, action.
   - `transition`: will be written.
   - `changed_in_source`: skipped. The status changed after the mark.
   - `needs_reason`: `blocked` without a note. Ask the user for a reason.
   - `unknown_key`: skipped.
5. Ask the user. Write nothing before the user says yes in the session.
6. After yes, per `transition` row: `todo_transition(todo_key, status, expected_version)` with the version just read. For `blocked`, the note is the `blocked_reason`. For other statuses, a non-empty note goes to the ToDo's item with `create_or_extend_note`.
7. Remove each written key from `todostate/flags`, `todostate/seen` and `todostate/notes` (read, drop the key, `set` with `if_version`). Keep rows that were skipped.
8. Run the ToDo recipe again.

### /dashboard add <preset> <tile>

A list tile is named `list:<skill-id>`: kind `list`, `skill_id` `<skill-id>`.

1. Add the tile to the private preset:
   `presets.add_tile(name, kind, skill_id=..., repo_dir='<skill dir>')`. It returns the
   private preset. The new tile is the last entry of its `tiles`, and it always has an
   `id`: the kind, `<kind>-2`, `<kind>-3` for repeats, or `list:<skill-id>`. When the
   private preset had no tiles yet, add_tile first copies the repo preset's tiles, so
   the preset keeps them.
2. Read `meta/layout` from the page database with `ArtifactData` `get`. Each item of
   `meta/layout` has the shape `{id, kind, x, y, w, h}`, and every `id` is unique.
3. `meta/layout` exists: `presets.append_to_layout(items, new_tile)` returns the items
   with the new tile below the lowest one. Write `{items: <that list>}` with `set` and
   `if_version`.
4. `meta/layout` does not exist (nobody has moved a tile on this page yet): write
   `{items: presets.layout_items(<all tiles of the preset, new tile included>)}` with
   `set`, without `if_version`. These are the ids the page itself gives the preset's
   tiles. Never write a layout that holds only the new tile: the page would then show
   only that one tile.

## Publishing

1. Copy `<skill dir>/template/page.html` to a file in the scratchpad.
2. In the copy, replace every occurrence of:
   - `__PRESET__` with the preset name,
   - `__TITLE__` with the page title (it occurs twice),
   - `__LAYOUT__` with the JSON of the preset's `tiles`, with every `<` written as `\u003c`.
3. Call `Artifact` publish with:
   - `file_path`: the copy,
   - `files`: `{"tiles.js": "<skill dir>/template/tiles.js"}`,
   - `capabilities`: `{db: {rules: [{path: "", read: "view", write: "admin"}]}, tts: {}, comments: {}}`,
   - `icon` on the first publish. On a republish pass the same `url`.
4. First publish only: `presets.set_url(name, url)` stores the address in the private file.

The preset's layout is used for the first build only. After that the page keeps its
layout in `meta/layout`. A republish never writes `meta/layout`.

## Answering a refresh comment

The page sends a comment with exact text. Only text that `parseCommand` in
`template/tiles.js` accepts counts:

- `dashboard refresh <preset> <tile|all>`
- `dashboard sync <preset>`

Steps:

1. Read the thread with `ArtifactComments`. If a Claude reply is newer than the request, do nothing. Another session answered.
2. Text that `parseCommand` rejects: do nothing.
3. `refresh`: run the recipe of that tile, or all. `sync`: only list the planned changes in the reply. Write only after a yes in the session.
4. Reply in one line, for example "Aufgaben aufgefrischt, 12 Einträge." Then resolve the thread.

## Offering a tile from another skill

Write one document `lists/<skill-id>` with `{v: 1, title, syncedAt, source, items: [{title, link?, status?, date?, group?}]}`. At most 500 items. The page lists it in the drop-down. See `tiles/list.md`.

## Confidentiality

This repo is shared. Project keys, space keys, page URLs, customer names and people's
names stay in the private file and in the page database.

- Titles of ToDos and tickets go only into the page database. Never into the repo, a commit message or a test fixture.
- Run `bash <skill dir>/scripts/check-clean.sh` in the repo checkout before every commit. It must print `clean`. It prints `no private file, nothing to check` when the private file does not exist.
- The check greps the repo for these fields of the private file, and only these: `denyList` entries; preset names (except names of repo presets, such as `global`); per preset `url`; `sources` values, also split at commas, semicolons and spaces; `filters` values, also split at commas and semicolons; tile `id`s without the `list:` prefix (ids made from a kind alone, such as `note-2`, are skipped). Values shorter than 3 characters are skipped. Put every other secret value, for example a customer name in a page title, into `denyList`.
- Then review with the `skill-confidentiality-boundary` skill.
- German page labels and field names are not confidential.
