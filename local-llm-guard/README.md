# local-llm-guard

A stdio MCP server for Claude Code. It hands small files that hold secrets or personal data to a local Ollama model. Claude Code never sees the file. It gets a filtered answer.

The server also edits such files. The local model proposes a change. You review the real diff in a macOS dialog and approve it. Claude Code only gets the outcome and a masked diff.

## Requirements

- macOS (the approval dialog uses `osascript`)
- [`uv`](https://docs.astral.sh/uv/)
- Ollama running on the same machine, with the model pulled: `ollama pull qwen2.5:14b`
- Python dependency `mcp>=2.3` (installed by `uv sync`; it brings `httpx2`)

## Install

Run this in the `local-llm-guard` folder:

```bash
make install
```

This runs `uv sync`. Then it registers the server in Claude Code at user scope, with this command:

```bash
claude mcp add --scope user local-llm-guard -- uv run --directory <this folder> local-llm-guard
```

Restart Claude Code after the install.

### Settings

Defaults come from environment variables in the registration.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOCAL_LLM_GUARD_MODEL` | `qwen2.5:14b` | Ollama model name |
| `LOCAL_LLM_GUARD_NUM_CTX` | `16384` | Context size in tokens |
| `LOCAL_LLM_GUARD_TIMEOUT` | `300` | Time limit for one model call, in seconds |
| `OLLAMA_HOST` | local default | Must point to the loopback interface (this machine). Other hosts are refused. |
| `LOCAL_LLM_GUARD_AUTO` | not set | `1` tells Claude Code to call the tools directly. Without it, Claude Code asks you first. |

To set a variable, register the server again with `-e`:

```bash
claude mcp remove --scope user local-llm-guard
claude mcp add --scope user -e LOCAL_LLM_GUARD_AUTO=1 local-llm-guard -- uv run --directory <this folder> local-llm-guard
```

## How Claude Code uses it

The server sends instructions to Claude Code. When the `sensitive-canary` hook blocks a read, or you say a file holds customer or personal data, Claude Code:

1. Tells you in one line which file was blocked and asks if it may hand the file to the local model. (With `LOCAL_LLM_GUARD_AUTO=1` it skips the question.)
2. Prints one command line for you to run with `!`, then stops and waits. See the next section.

A "yes" covers one file only.

## Use without MCP (when sensitive-canary blocks the tool call)

The `sensitive-canary` hook also blocks the MCP tool calls, because the path of the blocked file is in the tool input. So Claude Code prints a command, and you run it yourself with `!` in Claude Code:

```bash
! uv run --directory <this folder> local-llm-guard ask '/abs/path/file.txt' -q 'Which port is used?'
! uv run --directory <this folder> local-llm-guard task '/abs/path/file.txt' -i 'Summarize the settings'
! uv run --directory <this folder> local-llm-guard edit '/abs/path/file.txt' -i 'Change the port to 9090'
! uv run --directory <this folder> local-llm-guard status
```

A `!` command runs as you, outside the PreToolUse hook. Only the filtered answer goes into the chat. The command uses the same checks, masking and output filter as the tools, and `edit` shows the same approval dialog. When something fails, the result starts with `error:` and the exit code is 1. `local-llm-guard serve`, or no argument, starts the MCP server.

## Tools

| Tool | What it does |
| --- | --- |
| `local_ask(paths, question)` | Answers a question about up to 5 files. Returns a filtered answer. |
| `local_task(paths, instruction)` | Runs an instruction on up to 5 files. Returns a filtered answer. |
| `local_edit(path, instruction)` | Edits one file after you approve the diff. Returns approved or rejected, plus a masked diff. |
| `local_status()` | Shows the Ollama version, model, `num_ctx`, timeout and installed models. |
| `local_config(num_ctx, model, timeout_s)` | Changes these values until Claude Code restarts. Claude Code should ask you first. |

## How an edit works

1. The model proposes a list of changes.
2. The list is checked against the file.
3. A dialog asks `local-llm-guard: approve change to <file name>?`. It says that Claude wants to change a file and that only you can approve it. It names the process that asked (the server and the Claude Code process that started it). It shows the full path, how many lines are removed and added, and the real diff (without the `---` and `+++` header lines). If a change touches a line that holds a secret value, the first line of the dialog says: `[Warning: this change touches a line with a secret value.]`
4. The buttons are Write (save, a backup is made first) and Cancel (default, change nothing). If you do not answer in 120 seconds, this counts as Cancel.
5. The file hash is checked again, to see that the file did not change meanwhile.
6. A backup is written.
7. The file is replaced in one atomic write.
8. Claude Code gets the outcome and a masked diff. If the diff has more than 20 changed lines (every `+` or `-` line after the first `@@` line counts), Claude Code gets only the counts, for example `+25/-25 lines`.

A change is refused before the dialog when its new text holds invisible characters: Unicode format or control characters other than tab and newline, and line or paragraph separators (for example a zero-width space or a right-to-left override). Such characters can make the dialog show something else than what is written.

The diff goes into the dialog only when it has at most 60 lines, at most 4000 characters, and no line longer than 200 characters. The dialog cannot scroll, so a bigger diff opens in TextEdit instead. If TextEdit cannot be opened, no dialog is shown and the edit counts as Cancel.

## Limits

- Small text files only. At most 5 files per call. No chunking. If a file does not fit in `num_ctx`, the tool returns an error with the numbers.
- The size check counts the exact text sent to the model: the system prompt, the file headers, the file text, and in `local_edit` the line numbers. One token each: a digit, an ASCII punctuation or symbol character, and every letter of a word that holds a digit (hex, base64, ids). A non-ASCII character counts as many tokens as it has UTF-8 bytes. Other letters and spaces count one token per 3 characters. 1024 tokens stay free for the answer, and the answer may not be longer than that.
- After the model call, the tool asks Ollama how many prompt tokens it read. If the prompt filled the context, if Ollama read far fewer tokens than expected for a big prompt (Ollama cuts a too-long prompt to about half of `num_ctx` without an error), or if the answer was cut off, the tool returns `error: input or answer did not fit the context` and no model text.
- `local_ask` and `local_task` refuse an answer that repeats the files: `error: answer repeats the file content`. This happens when the answer holds at least half of the file lines (lines of 8 characters or more) word for word. Files with fewer than 5 such lines are not checked.
- Files whose name contains `.env` are always refused.
- Secrets are masked before the model sees the file. The rules cover, among others: keys whose name holds a credential word in any case (`password`, `pass`, `pw`, `pwd`, `passwort`, `kennwort`, `token`, `secret`, `key`, also inside names like `DB_PASS` or `db.pw`), XML elements and attributes with such names, `.netrc` lines, command line flags (`--password v`, `--token v`, and `-p v` after a database command), YAML block values and JSON arrays below such keys, and sentences like `the password is X`. The same rules run again on the answer. Masking too much is accepted; masking too little is not. If a known secret appears in the answer (also in encoded form), the answer becomes an error.
- Masking of personal data (e-mail, phone, IBAN, and names found by a second local model call) is best effort. It is not a guarantee.
- Business numbers stay visible on purpose.
- "Ask first" is an instruction to Claude Code. It is not a technical lock.
- `local_config` changes last only until Claude Code restarts. A refused value comes back with the reason, for example `error: num_ctx 1024 is out of range: allowed 2048 to 32768`. When the same call changes the model, `num_ctx` is checked against the maximum of the new model.
- The connection to Ollama ignores proxy settings (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) and `.netrc`. A proxy could send the file to another machine.
- Files that mix CRLF and LF line endings cannot be edited. Files that already contain text like `<SECRET_1>` cannot be edited.
- A long diff opens in TextEdit (see "How an edit works"). The temporary file is deleted after the dialog. The TextEdit window still shows the real values until you close it. macOS may also keep the window content in its saved state.
- Backups are kept for 30 days in `~/.local/state/local-llm-guard/backups`. Old backups are deleted when the server starts. If the folder cannot be read, this step is skipped and the server starts anyway.

## Measured cost of the context size

Measured on an Apple Silicon Mac with `qwen2.5:14b`, with the prompt filled to about 80% of the context.

| num_ctx | Time | Memory |
| --- | --- | --- |
| 16384 | 44.2 s | 11.9 GB (all in GPU memory) |
| 32768 | 105.3 s | 15.2 GB (all in GPU memory) |

You can repeat the measurement with `make measure`.

## Sandbox notes

A spike inside the `nono` sandbox showed that:

- Ollama on 127.0.0.1:11434 was reachable.
- The `osascript` dialog worked.
- The backup folder was writable.
- A blocked file was readable.

Editor-extension sessions may run without the sandbox. If a path is denied, the tool returns an error that names the path and the sandbox.

## Development

```bash
make test    # pytest
make check   # ruff, format check, confidentiality scan
```

## Uninstall

```bash
make uninstall
```

This removes the registration from Claude Code. Backups stay in `~/.local/state/local-llm-guard/backups` until you delete them.
