---
name: setup-voice-mode
description: Use when someone wants Claude Code to speak its answers aloud with the open-source voicemode MCP server and a local text-to-speech service on macOS, wants to pick a non-English voice, or asks how such a setup works, how to check it, or how to remove it.
---

# Setup Voice Mode — spoken answers from Claude Code

## Overview

[voicemode](https://github.com/mbailey/voicemode) is an MCP server (a tool server that Claude Code
can call). Its `converse` tool turns text into speech and plays it.

This skill sets up the **speak-only** variant:

- Claude speaks. Nothing listens. You keep typing or use your own dictation app.
- The speech comes from a **local** service on `127.0.0.1`. No text leaves the machine.
- Claude speaks a short version of each answer when you ask for it with a trigger word.

Why speak-only: voicemode can also record your microphone. If another app already uses the
microphone (a dictation app, for example), a second listener records the speaker output.
Speak-only avoids that.

## Parts

| Part | What it is | Where it runs |
|---|---|---|
| voicemode clone | Python package with the MCP server | a checkout you reviewed, run with `uv run --directory <clone> voicemode` |
| mlx-audio | OpenAI-compatible TTS server for Apple Silicon | launchd service on `127.0.0.1:8890` |
| TTS model | Kokoro-82M (English, fast) or Qwen3-TTS (German and other languages) | downloaded by mlx-audio on the first request |
| Rule file | When and how Claude speaks, see [voice-rule.md](voice-rule.md) | imported into your global `CLAUDE.md` |

## Steps

1. **Review the clone before running anything.** Use the `repo-install-safety-check` skill on the
   voicemode checkout. Run only code you reviewed.
2. **Use the script.** [scripts/setup-voice-mode.sh](scripts/setup-voice-mode.sh) installs mlx-audio
   as a service, waits for it, and registers the MCP server. Copy it, set `REPO`, read it, then run it
   yourself. Agents in auto mode are often blocked from running code from a cloned repo; that is
   expected. Write the script to a temporary file and ask the user to run it.
3. **Add the rule.** Copy [voice-rule.md](voice-rule.md) next to your global instructions and import
   it, for example with a line `@<path>/VOICE.md` in `~/.claude/CLAUDE.md`. Change the trigger
   words to the ones you want to say or type.
4. **Restart Claude Code.** In VS Code: Command Palette → "Developer: Reload Window", then resume
   the session. MCP servers read their environment at start.
5. **Test.** Ask for a spoken answer with a trigger word.

## Keep the local URLs

voicemode's default URL lists try the local service first and then `https://api.openai.com/v1`.
Set both lists to local addresses so text never goes to a cloud service by accident:

```bash
claude mcp add --scope user voicemode \
  -e VOICEMODE_TTS_BASE_URLS=http://127.0.0.1:8890/v1 \
  -e VOICEMODE_STT_BASE_URLS=http://127.0.0.1:2022/v1 \
  -- uv run --directory <clone> voicemode
```

Nothing listens on the STT address on purpose. Without that line voicemode falls back to OpenAI.

## Do not install the plugin

The repository is also a Claude Code plugin with six global hooks (before and after every tool call,
notifications, stop, compaction, permission requests). They play sounds. For speak-only use you do
not need them. Register only the MCP server, as above.

## Speech language and model

The default voice is Kokoro `af_sky`. Kokoro has **no German voice**. German text sent to it is
spoken with an English accent.

mlx-audio also serves **Qwen3-TTS** (Apache-2.0, German supported). Measured on one Apple Silicon
machine:

| | Kokoro-82M | Qwen3-TTS 0.6B CustomVoice |
|---|---|---|
| Time to generate | 0.6 s for 6.8 s of audio | 4.9 s for 11.7 s of audio |
| First call | model download | about 2 min 20 s, model download |
| German | English accent | "much better, a slight English accent remains" (listener's words) |

To use it, set in the MCP registration:

```bash
-e VOICEMODE_TTS_MODELS_MLX_AUDIO=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16 \
-e VOICEMODE_VOICES=Ryan
```

Other speakers of that model: `Aiden`, `Vivian`, `Serena`. A larger model with better quality is
`mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16`.

**Known limit (voicemode 9.0.2):** voicemode accepts a voice only if it is in the endpoint's voice list.
For mlx-audio this list is the fixed Kokoro set, and the server cannot report others. A voice such as
`Ryan` is therefore not found without a small patch: add the voices from `VOICEMODE_VOICES` to the
seed list in `voice_mode/provider_discovery.py` (and in `voice_mode/tools/providers.py`). Check whether
a newer upstream version already does this.

Qwen3 treats an unknown `lang_code` such as the default `a` like `auto` and detects the language
from the text, so no language patch is needed.

Not suitable: Voxtral TTS (non-commercial licence) and KugelAudio (about 17 GB).

## Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| First request downloads the model | voicemode stops waiting after about 48 s, the first call fails with "All TTS attempts failed" | Warm the model once with `curl` against `http://127.0.0.1:8890/v1/audio/speech` and wait, or call again |
| `converse` default `wait_for_response=true` | A plain `message=` call opens the microphone | Always use `turns` with `say` only |
| Whole answer is generated before playback | With Qwen3 the sound starts a few seconds late | Keep spoken text short; the rule file asks for 2 to 4 sentences |
| Sandboxed shell (for example a `nono` profile) | The MCP server may fail to start if `$HOME/.voicemode` is not writable | Add that directory to the sandbox grants; the VS Code extension is often not sandboxed |
| Security hook blocks reads of the clone | Files with emails or key-looking lines are blocked | Disable the hook for the review, never work around it |

## Check

```bash
claude mcp get voicemode
curl -s http://127.0.0.1:8890/v1/models
uv run --directory <clone> voicemode service status mlx-audio
```

## Remove

```bash
claude mcp remove --scope user voicemode
uv run --directory <clone> voicemode service uninstall mlx-audio   # command name not verified
```

Then remove the `@…/VOICE.md` import line from `~/.claude/CLAUDE.md`.

## Related skills

- `repo-install-safety-check` — review the clone before step 2
- `skill-confidentiality-boundary` — keep your own copy of the rule file free of private details
