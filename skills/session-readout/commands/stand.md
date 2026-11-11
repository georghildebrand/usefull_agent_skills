---
description: Read the current state of this session aloud in a small window (close the window to stop the sound)
argument-hint: "[optional focus, e.g. only the deploy]"
---

Write a short spoken status of this session. The user is about to walk away for a few
minutes and listens on headphones.

Content, 4 to 6 sentences:
- what we are working on,
- what is done,
- what is running right now,
- what waits for a decision or action by the user.

Scope: the current state of the whole session. If a focus is given here, cover only that: $ARGUMENTS

Form:
- The language the user writes in. Plain, full sentences that sound natural when spoken,
  even when a terse writing mode is on.
- No code, commands, file paths, URLs, ticket numbers, IDs, tables or lists. Say what a
  thing is instead of its name ("the deploy script", not its file name).
- One sentence per line.

Then:
1. Show the sentences in the chat.
2. Run this once, with the sentences between the markers:

```bash
stand-speak --session "<folder name> · <topic in 3 to 5 words>" <<'TEXT'
<sentence 1>
<sentence 2>
TEXT
```

3. Do not wait for the sound, do not run it again, do not check whether it played. The
   window plays the sound by itself and the user stops it there. If the command fails,
   say so in one line and stop.

Do not use any other tool that makes sound.
