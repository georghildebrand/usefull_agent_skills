# Tile: sessions

Document: `sessions/list`.

## Source

Local files only: `~/.claude/sessions/*.json` and the transcripts
`~/.claude/projects/*/<sessionId>.jsonl`. Claude Code does not document this format,
and it can change. The builder skips fields it does not find.

## Build

`<skill dir>` is explained in SKILL.md.

```
python3 <skill dir>/scripts/build_sessions.py <scratchpad>/sessions.json
```

Write the file with `ArtifactData` `set` to `sessions/list`, with `if_version`.
Items carry: name, kind, state, startedAt, lastActiveAt, cwd (home shortened to `~`), hasTranscript.
The tile shows `state` as stored. It does not decide itself what "running" means.

## Left out

Transcript content, prompts, process ids.
