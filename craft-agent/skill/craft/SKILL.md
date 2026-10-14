---
name: craft
description: Edit, convert or create files with the ArtCraft desktop tools (PDF, Word documents, spreadsheets, photos, raw photos, vector graphics, UI designs, CAD drawings, page layouts, video, audio). Use when the user types /craft or asks to do such a task with ArtCraft. Picks the matching craft-<tool> agent, copies the inputs into a job folder and reports the result files.
---

# /craft

One entry point for 11 `craft-<tool>` agents. Each agent controls one ArtCraft
application through its MCP server. An agent can only reach files inside a job
folder; a hook blocks every other path.

## Steps

### 1. Pick the agent

Match the input file type first, then the task. If two agents fit, ask the user
one question. If none fits, say so and stop.

| Input or task | Agent | Tool key |
|---|---|---|
| `.pdf`: pages, merge, split, comments, forms, passwords, redact | `craft-pdf` | `pdf` |
| `.docx` `.odt` `.rtf` `.md`: write, edit, convert documents | `craft-word` | `word` |
| `.xlsx` `.csv` `.ods`: data, formulas, charts | `craft-sheet` | `grid` |
| `.psd`, or one image: layers, masks, retouch, text | `craft-photo` | `photo` |
| raw files, `.dng`, many photos: exposure, color, batch export | `craft-light` | `light` |
| `.svg` `.ai` `.eps`: vector drawing, logos, icons | `craft-vector` | `vector` |
| `.figcraft`, UI screens, components, prototypes | `craft-fig` | `fig` |
| `.dxf` `.dwg`: technical drawings | `craft-cad` | `cad` |
| `.idml`, page layout, brochures, `.epub` | `craft-design` | `design` |
| `.mp4` `.mov` `.mkv`: cut, color, captions, export | `craft-film` | `film` |
| `.wav` `.mp3` `.flac`, several tracks: record, edit, mix | `craft-sound` | `sound` |

Cases that need a question:
- `.jpg` `.png` `.tif`: one image with pixel work goes to `craft-photo`; many photos
  or exposure and color work goes to `craft-light`.
- A `.pdf` the user wants to rewrite as a document: `craft-pdf` (edit the PDF) or
  `craft-word` (new document).

### 2. Check that the tool is built

Run `craft-mcp --check <tool key>`. On exit 4, show its message to the user (it
names the `make build` command) and stop. Do not start the agent.

### 3. Create the job

Slug: `YYYY-MM-DD-<2 to 4 words of the task, kebab-case>`, with today's date.
Run `craft-stage <slug> <input files>`. It prints the job folder. Without input
files (create a new file), run `craft-stage <slug>`.

Input files must lie inside `CRAFT_READ_ROOT` (set in `config.env`).
`craft-stage` refuses other files. If a file is outside, ask the user to copy it
into the read root first. Pass plain paths, not `file://` URLs.

On exit 2, show the message and stop. Never copy a refused file in another way,
and never put files into the job folder yourself.

### 4. Hand over to the agent

Use the Agent tool with `subagent_type: craft-<tool>` and this prompt:

    Task: <the user's task, with the file names as they are in <job>/in>
    Job folder: <the absolute path craft-stage printed>
    Inputs: <job>/in/<name> (one line per input)
    Results: write to <job>/out
    Mode: headless

Write `Mode: live` only when the user asked to watch the app or said "live". The
user must start the app first with `craft-app <tool key>`.

### 5. Report

Tell the user each output path, what the agent checked, and what it could not
do. If the agent saved anything under `out/_failed/`, say that first. Offer to
open a result with `open <path>`.

## A task that needs two tools

Run the agents one after another with the same job folder. Hand the first
agent's output files to the second agent as its inputs (they are already in
`<job>/out`; name them in the prompt). Do this only when the task clearly needs
two tools.

## Do not

- Do not call `craft-mcp` or the ArtCraft CLIs yourself to do the task.
- Do not give the agent paths outside the job folder.
- Do not retry a refused or blocked file with a different path.
