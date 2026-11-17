# Tile: todos

Document: `todolists/<project>` (one per ToDo project in `sources.todos`).
The page also writes `todostate/flags`, `todostate/seen` and `todostate/notes`. The recipe never writes these.

## Source

Per project in `sources.todos`, call the zotero2ai tool
`todo_list(project=<project>)`. The harness saves the result to a file.
Use that file path as `<tool-result-file>`.

## Build

```
python3 skills/dashboard/scripts/build_todos.py <tool-result-file> <project> <scratchpad>/todos-<project>.json
```

Write the output file with `ArtifactData` `set` to `todolists/<project>`, with `if_version` from the last read.
Items carry: key, title, status, priority, version, updatedAt, createdAt, order. The builder removes the
`[MEM][todo][...]` prefix from titles, keeps only `todo`, `in_progress` and `blocked`, and cuts the document at 256 KiB.

If a project is gone from `sources.todos`, delete its `todolists/<project>` document.

## Left out

Descriptions, owners, session ids, done and cancelled ToDos. Marks are written back only by `/dashboard sync`.
