# local-llm-guard: local model tools for files Claude must not see

Date: 2026-11-09
Status: design, not built

## Intent

Some files cannot go to a cloud model. Two kinds:

1. **Files with secrets.** The `sensitive-canary` plugin (a `PreToolUse` hook on `Read` and
   `Bash`) blocks any file that contains an e-mail address or a `.env`-style `KEY=value`
   line. Examples: `~/.claude.json`, a CLI config file that holds access tokens, a project
   `.env`. Claude then cannot answer a simple question such as "which MCP servers are
   registered" or "which host does profile X point to".
2. **Files with customer or personal data.** Data that must stay on the machine for privacy
   reasons, for example a customer spreadsheet.

Target setup: a local Ollama install with `qwen2.5:14b` (tested against Ollama 0.40.x). The idea: a small local tool that
lets every Claude Code session hand such a file to the local model. The local model reads the
file and does the work. Claude gets only a filtered answer, never the file content.

## Goals

- Every Claude Code session (main session and subagents) can call the tools. Registered once as
  a stdio MCP server in user scope.
- **Read:** Claude asks a question about one or more files and gets an answer in which secrets
  and personal data are masked.
- **Edit:** Claude describes a change to a file. The user sees the full, unmasked diff in a
  macOS dialog and approves or rejects it. Only after approval is the file written, with a
  backup. Claude gets back "approved" or "rejected" plus a masked diff.
- **Local task:** Claude gives a free task over files (summarise, extract, compare). Same
  filtering as Read.
- One small Python program. Few dependencies.

## Non-goals

- No Claude Code session that runs fully on Qwen (`ANTHROPIC_BASE_URL` pointing at Ollama).
  Tool access from normal sessions is enough. Note: such a session would not
  help anyway, because hooks run independent of the model.
- No cost saving or bulk work. The purpose is privacy.
- No new subagent type. Subagents use the MCP tools like any other tool.
- Writing new secret values (for example a rotated token) is out of scope. Claude would have to
  know the value to pass it.

## Anti-goals (failure even if it works)

- **Any secret value reaches Claude**, in any form: plain, base64, with spaces between
  characters, reversed, split over lines. A file may contain text that tries to make the model
  do this (prompt injection), so this must hold even when the model follows hostile
  instructions.
- **A file is changed without the user's click** in the dialog.
- **A file is processed silently in part.** Ollama cuts the input at its context size
  (`num_ctx`, default only a few thousand tokens) without an error. An answer based on half a
  file must not be returned as if it covered the whole file.
- The tool becomes a general way around `sensitive-canary` that returns raw content.

## Constraints

- macOS, Python via `uv`. Ollama on `http://127.0.0.1:11434`.
- Claude Code may run inside a filesystem sandbox such as `nono`. A stdio MCP server started
  by Claude inherits that sandbox. It can only read the paths the sandbox profile allows, and
  it needs network access to `127.0.0.1:11434`. Some ways of starting Claude Code (for example
  an editor extension) may run without the sandbox. The tool must report a clear error when a
  path is denied, not a model answer about nothing.
- The repository is meant to be shareable: no customer names, no internal hosts, no real
  secrets in code, docs or test fixtures. Test data is synthetic.
- Fits the repo layout: its own top-level directory `local-llm-guard/` with a `Makefile`
  (`make install`, `make check`, `make test`) and a row in the README.

## How it works (decided)

### Masking happens before the model, not only after

For secrets, the program scans the file **before** sending it to Qwen and replaces every
secret value with a placeholder (`<SECRET_1>`, `<SECRET_2>`, ...). It keeps the mapping in
memory only. Qwen never sees a secret value, so it cannot leak one, whatever the file tells it
to do. Questions such as "which host does profile X use" still work, because hosts and keys
are not secrets.

The detection should match `sensitive-canary`: same patterns (`KEY=value`, known token
prefixes, private keys, e-mail) plus an entropy check for random-looking strings. Reuse the
canary's rule set if it can be called or read in a stable way; otherwise reimplement the same
categories and test against the same kinds of input.

### Output filter after the model

The answer from Qwen passes a second filter before it goes to Claude:

- The secret detector again (in case a secret was not caught on input).
- Personal data: e-mail addresses, phone numbers, IBAN-like numbers, by pattern.
- Person names: patterns cannot find names. A second call to the same local Qwen model gets
  only the answer text and returns the person names in it as JSON. The program then masks
  them as `<NAME>`. No network call leaves the machine.
- Business numbers (revenue, prices, quantities) stay visible. This is a deliberate choice:
  the tool protects personal data and secrets, not business figures. Phone numbers and IBANs
  are still masked by pattern, even when they look like plain numbers.

**Fail closed:** if any filter step fails or times out, the tool returns an error and no
answer.

### Edit flow

1. Claude calls the edit tool with a path and a plain-text instruction.
2. The program masks secrets in the file (same placeholders) and sends the masked file plus
   the instruction to Qwen.
3. Qwen returns only a small structured change list: line number, old line, new line. It does
   not rewrite the whole file. This keeps a 14B model from dropping or changing other lines.
4. The program checks each old line against the masked file. Any mismatch: abort.
5. The program puts the real secret values back into the placeholders and builds the real diff.
   A new line may not contain a placeholder that was not in its old line.
6. A macOS dialog (via `osascript`) shows the full path of the file in its title and first
   line, then the full unmasked diff, with two buttons, write or cancel. Claude has no way to press the button.
7. On approval: compare the file's SHA-256 hash with the hash taken before the dialog. If
   the file changed while the dialog was open, abort. Otherwise write a backup (see
   "Backups" below), then write atomically: a temporary file in the same directory, then
   rename. The file mode, line endings and trailing newline stay as they were.
8. Claude receives the result (approved / rejected / aborted and why) and the diff with
   secrets and personal data masked.

### Hand-off when sensitive-canary blocks a file

The main use: `sensitive-canary` blocks a `Read` or `Bash` call, and Claude then offers the
local tools instead of stopping.

- The MCP server sends an `instructions` text. Claude Code loads it into every session where
  the server is registered. The text says: when `sensitive-canary` blocks a file, tell the
  user in one short line which file was blocked and why, and ask whether to hand it to the
  local model. Mention the allow tag as the other option. Call `local_ask`, `local_task` or
  `local_edit` only after the user says yes. A yes covers that one file only. For any other
  file, Claude asks again.
- Files named `.env` or `.env.*` are never offered and never read. Every tool refuses them
  before it opens the file.
- **Asking first is the default.** A setting (environment variable in the MCP registration,
  for example `LOCAL_LLM_GUARD_AUTO=1`) switches the instructions text to "call the local tool
  directly, then report what you did". The program reads the setting at start-up.
- This rule lives in the server's `instructions`, not in a `CLAUDE.md`. So it is only active
  when the server is registered, and Claude never points to a tool that does not exist.
- The plugin `sensitive-canary` is not changed. It stays the first protection layer.
- Limit: "ask first" is an instruction to Claude, not a technical lock. `local_ask` and
  `local_task` have no dialog of their own. The technical locks are the masking and the
  output filter, plus the dialog for `local_edit`.

### Tool list

| Tool | Input | Returns to Claude |
| --- | --- | --- |
| `local_ask` | paths, question | filtered answer |
| `local_task` | paths, task text | filtered result |
| `local_edit` | path, change instruction | approved/rejected/aborted, masked diff |
| `local_status` | none | Ollama reachable, model name, context size |
| `local_config` | optional new context size, model name, timeout | the settings now in use |

### File size: small files only, no chunking

The tool is built for small files: config files, `.env` files, short documents, small tables.
It does **not** split large files into chunks. Chunking would need a merge step over partial
answers, and on a single laptop that is slow and hard to get right.

- Default context size (`num_ctx`): 16 384 tokens. Upper limit: the model's own maximum, read
  from Ollama at start-up (32 768 for `qwen2.5:14b`).
- At most 5 files per call. Binary files (a NUL byte, or not valid UTF-8) are refused.
- Before calling the model, the program estimates the tokens of prompt plus files as
  `ceil(characters / 3)` and keeps 1 024 tokens free for the answer. This estimate is
  conservative: it counts more tokens than the real tokenizer for normal text. If it does not fit, the tool refuses with a clear message: file
  name, estimated tokens, current limit, and the hint that `local_config` can raise the limit.
- The same rule goes into the `instructions` text, so Claude knows the tool is for small files
  and does not hand it a large export.
- Reference machine: an Apple Silicon Mac with about 32 GB or more unified memory. The full
  32 768 tokens are expected to fit in memory there, but this is not measured. The first build step measures memory use and answer time at
  16 384 and 32 768 tokens and writes the numbers into the README.

### `local_config`

Lets Claude change how the local model runs, for example raise the context size for a larger
file or pick another installed model.

- Changeable: context size (between 2 048 and the model's maximum), model name (only models
  that `ollama list` shows), request timeout.
- **Not changeable:** anything about masking, the output filter, the dialog, or the backup.
  These have no setting at all, so no tool call can switch them off.
- Claude calls `local_config` only after the user said yes in the same turn.
- Changes last only for the running server process. Nothing is written to disk. At the next
  start the defaults apply again.
- Defaults come from environment variables in the MCP registration, set only by the user:
  `LOCAL_LLM_GUARD_NUM_CTX`, `LOCAL_LLM_GUARD_MODEL`, `LOCAL_LLM_GUARD_TIMEOUT`. Without
  them: 16 384 tokens, `qwen2.5:14b`, 300 seconds. No tool changes these variables or the
  registration.

Every result also states: which files were read, their size in tokens, and whether they fit
into the context. If a file does not fit, the tool refuses and says so.

### Local only

- The Ollama endpoint must be a loopback address (`127.0.0.1`, `::1`, `localhost`). If
  `OLLAMA_HOST` points anywhere else, every call is refused with that reason.
- The model must be installed locally (`ollama list`) and must not be an Ollama cloud model
  (for example a `-cloud` tag). The same check runs when `local_config` changes the model.
- File content, model output and the unmasked diff never go to logs, stderr or error
  messages.

## Decisions made by the designer (check these)

These were settled without the user. They can be changed.

- **Input masking covers secrets only.** Personal data reaches the local model unmasked. That
  is fine, because the model runs locally. Personal data is masked on the output side, and the
  masked diff from `local_edit` hides both secrets and personal data.
- **What counts as a secret on input:** a value is masked when (a) its key name looks like a
  credential (`token`, `secret`, `password`, `passwd`, `api_key`, `key`, `auth`, `credential`,
  `private`), or (b) it matches a known token format (prefixes such as `ghp_`, `sk-`, `AKIA`,
  `dapi`, `xox`, PEM private key blocks, JWTs), or (c) it is a long random-looking string with
  high Shannon entropy. Hosts, URLs without credentials, profile names, paths and plain
  numbers stay visible. Masking too much is acceptable; masking too little is not. A URL with
  a user name and password before the host has the password part masked.
- **Encoded output:** for secrets, the guarantee comes from input masking: the model never had
  the value. The output filter still normalises the answer (removes whitespace, decodes base64
  and hex fragments, checks the reversed string) and scans again. Any hit of a known secret
  value from the input map: the whole answer is replaced by an error. Values shorter than 8
characters are not checked in encoded form, because short strings match by chance. For personal data, the
  output filter is best effort (patterns plus the name step), not a hard guarantee.
- **`sensitive-canary` rules:** reimplement the same categories in the program. Do not depend
  on the plugin's install path or internal file format. The test fixtures cover each category.
- **Dialog inside the sandbox:** whether a process inside `nono` can run `osascript` and show
  a dialog is not verified. The first build step is a small check for this. If the sandbox
  blocks it, the fallback is a different approval path, decided at that point
  (for example a small helper process started outside the sandbox that shows the dialog). Report the result before building
  the edit flow.
- **Dialog defaults:** timeout after 120 seconds. Timeout, a closed dialog, or no GUI session
  (for example over SSH) all count as reject.
- **Edits on lines with secrets:** a changed line must keep exactly the placeholders of its old
  line, in any position. So renaming the key of a secret line is allowed. Any change that
  removes, adds or alters a placeholder is rejected. Changing a secret value is not possible.
- **Backups:** stored in `~/.local/state/local-llm-guard/backups/` with directory mode `700`
  and file mode `600`, named `<original-path-with-slashes-replaced>.<timestamp>`. Not next to
  the original, so they cannot end up in a git commit. The program deletes backups older than
  30 days at start-up.

## Left to the builder

- MCP library (official `mcp` Python SDK or FastMCP) and the exact tool schemas.
- How the dialog shows a long diff (dialog text field, or a temporary file opened in a viewer
  that is deleted afterwards).
- Test fixtures: synthetic files with fake secrets, fake names, and an injection file that tells
  the model to print secrets encoded. The test passes when none of the fake secret values
  appears in any tool result in any encoding.
