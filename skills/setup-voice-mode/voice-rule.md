# Spoken answers (voicemode)

Template. Copy it to a file next to your global instructions (for example `~/.claude/VOICE.md`),
change the trigger words to your language, and import it from your global `CLAUDE.md`.

---

The voicemode MCP server speaks text through a local TTS service on `127.0.0.1:8890`. The user types
prompts or dictates them with a separate app, so voicemode never listens.

## Trigger words

The user says or types these. Dictated prompts arrive as plain words, not markup.

| User says | Effect |
| --- | --- |
| "Read aloud: ..." at the start of the prompt | Speak this one answer, in addition to the normal text answer. |
| "Read aloud from now on" | Speak every answer until "Read aloud off" or the end of the session. |
| "Read aloud off" | Stop speaking answers. |

Typed aliases: `[read]`, `[read on]`, `[read off]`.

Dictation can change spelling and punctuation ("Read aloud,", "read a loud"). Match the sound, not
the exact spelling. Do not speak because the phrase appears inside a normal sentence, for example
"the script should read aloud the file". Only the three forms above count.

## How to speak

- Call the voicemode `converse` tool with `say` turns only. Never use `ask` turns and never set
  `wait_for_response` to true: the microphone belongs to the dictation app, and a second listener
  records the speaker output.
- Speak a short version of the answer: 2 to 4 sentences, in the language of the prompt, in plain
  full sentences. No terse or telegraphic style, even when such a mode is on.
- Never speak code, paths, commands, tables, URLs or IDs. Those stay in the text.
- Speak after the text answer is written, as the last step of the turn.
- Before every spoken answer, run `test -e "$HOME/.voicemode/MUTE" && echo muted`. If it prints
  `muted`, do not speak and do not mention it. The flag is set by the kill switch (`voice off`, see
  `SKILL.md`).
- If `converse` returns a text that starts with `[control: stop]`, the user cut the speech on
  purpose. Continue in text. Do not speak again in this session until the user says a trigger word
  again.
- If the `converse` tool is missing or fails, say so in one line of text and continue. Do not retry,
  and do not install or start services to fix it.

## Optional: full read-aloud

Add a fourth trigger, for example "Read aloud in full: ...", if you want the whole answer spoken
instead of a short version. Speak it sentence by sentence, still without code, tables, paths and
URLs. With a slow model, expect the first sound a few seconds late for long answers.
