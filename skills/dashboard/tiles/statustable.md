# Tile: statustable

Document: `statustable/current`.

## Source

The `statustable` skill produces the rows in the session. This tile does not change that skill.

## Build

The dashboard session converts the current rows of the status table into one document. Write it with `ArtifactData` `set` and `if_version`:

```
{"v": 1, "source": "statustable", "syncedAt": "<now, ISO UTC, Z>",
 "items": [{"id": "<row id>", "workstream": "<name, first row of a group only>", "topic": "...",
            "context": "...", "state": "...", "next": "..."}]}
```

The page repeats a workstream for later rows of the same group, so write the name only in the first row of a group.

Optional fields per row (template 3): `recap` (one or two sentences, always visible), `detail` (longer text, shown on hover or tap) and `prio: "low"` (row is dimmed). If the session has no status table, run the `statustable` skill first, or leave the document alone and say so.

## Left out

Anything the status table itself does not show. Do not add detail the table does not carry.
