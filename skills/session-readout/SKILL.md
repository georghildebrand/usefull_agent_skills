---
name: session-readout
description: Use when someone wants a Claude Code session to read its current state aloud on demand (a short spoken "where do we stand" before stepping away), with the sound in a separate window that stops when the window closes, plays only on headphones, and never starts late. macOS only.
---

# Session readout: a spoken status in a window

## Overview

The user types `/stand`. Claude writes 4 to 6 plain sentences about the session state and
passes them to a launcher. The launcher opens a small native window. **The window plays the
sound.** Window and sound are one process, so closing the window ends the sound.

Why not an MCP speech server inside the session: there, sound belongs to the session
process. With many open sessions, any of them can speak, the user cannot find the window
that speaks, and a slow model makes the sound start minutes after the text. One case seen:
the sound started in the next meeting and could not be stopped.

## Rules built into the window

| Rule | How |
|---|---|
| Stop at once | Stop button, Escape, closing the window or Cmd+Q end the process |
| Headphones only | CoreAudio default output must be Bluetooth or the headphone jack. Without headphones the window shows the text and stays silent. If the output changes while speaking, the sound stops |
| Never late | Engine `auto` asks the local Qwen3 TTS server first. If its first sentence is not ready within 8 s, the macOS system voice speaks everything. Errors switch at once |
| One window | The launcher closes the old window before it opens a new one |
| Always visible | Sound only runs while the window is on screen; it floats above other windows |
| Closes itself | 5 s after the last sentence; 3 min after a silent stop |

The window shows: title, session label, time the text was written, status with sentence
number, engine and headphone name, and the full text with the current sentence in bold.

## Parts

| File | Installed as |
|---|---|
| [app/Sitzungsstand.swift](app/Sitzungsstand.swift) | `~/Applications/Sitzungsstand.app` (built with `swiftc`, no Xcode project) |
| [scripts/stand-speak](scripts/stand-speak) | `~/.local/bin/stand-speak` |
| [commands/stand.md](commands/stand.md) | `~/.claude/commands/stand.md` (symlink) |
| [scripts/install.sh](scripts/install.sh) | builds and installs all three |

The window texts and the default system voice are German. Change the strings in the Swift
file and `--system-lang` for another language.

## Install

```bash
bash skills/session-readout/scripts/install.sh
stand-speak --check     # output device, headphones yes/no, TTS server, system voice
```

Needs the Xcode command line tools (`swiftc`). The better voice needs an OpenAI-compatible
TTS server on `127.0.0.1:8890`, for example mlx-audio with
`mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16` (see `setup-voice-mode`). Without it,
the system voice speaks.

## Use

| Action | Effect |
|---|---|
| `/stand` | Spoken state of the whole session |
| `/stand only the deploy` | Spoken state of one topic |
| `stand-speak --stop` | Close the window from a shell |

Settings for the launcher: `STAND_ENGINE=auto|qwen|system`, `STAND_TTS_URL`,
`STAND_TTS_MODEL`, `STAND_TTS_VOICE`, `STAND_SYSTEM_LANG`, `STAND_SYSTEM_VOICE`. Set them in
the environment or, to keep them, in `~/.config/stand-speak.conf` (shell syntax, for example
`STAND_SYSTEM_VOICE="Anna (Premium)"`). They are passed as arguments, because `open` does not
pass environment variables to an app.

## System voice quality

macOS ships only the simple ("compact") voices. Much better "Enhanced" and "Premium" voices
can be downloaded: System Settings → Accessibility → Spoken Content → System voice → Manage
Voices → German. Without `STAND_SYSTEM_VOICE`, the window picks the highest quality voice
installed for the language. `stand-speak --check` shows which one it picks.

## Pitfalls

| Pitfall | What happens |
|---|---|
| Bluetooth speaker | Counts as headphones; CoreAudio reports the same transport type |
| USB headset | Does not count; extend `headphonesName()` if needed |
| Cold Qwen3 model | The first `/stand` after a pause often uses the system voice; the request still loads the model, so the next one is faster |
| Text written by the session | `/stand` waits until the session finishes its current step, because Claude writes the text |

## Related skills

- `setup-voice-mode` — the local TTS server and the earlier MCP-based approach
- `statustable` — the same content as a table
