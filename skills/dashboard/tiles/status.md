# Tile: status

Documents: `status/<id>`, and `status/current` for the state of the session that refreshes.

## Source

Text written by the session itself. No external call.

## Build

Write the status of this session in short plain sentences. Write `status/current` with `ArtifactData` `set` and `if_version`:

```
{"v": 1, "source": "status", "syncedAt": "<now, ISO UTC, Z>", "updatedAt": "<same>",
 "title": "<short title>", "order": 0, "text": "<spoken text>"}
```

The menu on the page lists all `status/*` documents by `order`. The page reads the text aloud with the `tts` capability. That works only in Chrome or Edge in the browser. The tile shows the text in every view.

## Left out

Anything that is not meant to be spoken or read by others: secrets, private names, long logs.
