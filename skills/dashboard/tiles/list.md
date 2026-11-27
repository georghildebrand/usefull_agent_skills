# Tile: list (generic)

Document: `lists/<skill-id>`. The tile id in a preset is `list:<skill-id>`.
Any skill can offer a tile by writing this one document. The page code does not change.

## Source

The skill that owns the list. It decides where its data comes from.

## Build

Write with `ArtifactData` `set` and `if_version`:

```
{"v": 1, "title": "<tile title>", "syncedAt": "<now, ISO UTC, Z>", "source": "<short label>",
 "items": [{"title": "...", "link": "https://...", "status": "...", "date": "<ISO>", "group": "..."}]}
```

Only `title` is required per item. Optional since template 3: `recap` (short text, always visible), `detail` (shown on hover or tap), `prio: "low"` (row is dimmed). At most 500 items; the page shows the first 500 and says so.
The document stays under 256 KiB. A malformed document shows "Diese Liste hat ein unbekanntes Format" on the page.
`<skill-id>` is one database path segment: letters, digits and `_ - . ~ : @ +`, at most 200 characters.
To put the tile on a page: `/dashboard add <preset> list:<skill-id>`.

## Left out

Anything the owner skill does not want others to see on a shared page.
