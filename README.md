# usefull_agent_skills

Reusable Claude Code skills collection. Each skill lives in `skills/<name>/SKILL.md` and is discoverable through the Claude Code `Skill` tool.

## Skills

| Skill | What it covers | Use when |
|---|---|---|
| [`atlassian-cli-setup`](skills/atlassian-cli-setup/SKILL.md) | Initial auth, profile setup, and recovery | You are first setting up `atlassian-cli` or fixing auth |
| [`atlassian-cli-usage`](skills/atlassian-cli-usage/SKILL.md) | Jira, Confluence, and Bitbucket runtime usage | You need to update issues, create PRs, or write ADF content |
| [`databricks-cli`](skills/databricks-cli-general-usage/SKILL.md) | Databricks CLI operations and debugging | You need job runs, SQL, clusters, or workspace assets from the terminal |
| [`repo2ai`](skills/repo2ai/SKILL.md) | Export a repository as structured Markdown context | You want to load a whole repo into context for review or analysis |
| [`graphify-usage`](skills/graphify-usage/SKILL.md) | Build/refresh a local AST knowledge graph per repo; code-only vs semantic mode, claude-cli backend, cron/launchd refresh instead of git hooks | You want fast structural orientation in one large/unfamiliar repo (not for cross-repo data contracts) |
| [`skill-confidentiality-boundary`](skills/skill-confidentiality-boundary/SKILL.md) | Keep skills generic and publish-safe | You are writing or reviewing a skill |
| [`aws-credential-resolution-order`](skills/aws-credential-resolution-order/SKILL.md) | AWS credential chain, silent env-var override, region split | Debugging "wrong account" auth or switching between profiles and session tokens |
| [`claude-code-unattended-bash`](skills/claude-code-unattended-bash/SKILL.md) | Three Bash patterns that block unattended sessions on approval prompts | Writing Bash for overnight jobs, background agents, or `/loop` polling |
| [`cross-repo-epic-review`](skills/cross-repo-epic-review/SKILL.md) | Four-round review structure for multi-repo epics | Reviewing a cross-team epic or deciding whether to split a phased epic |
| [`agent-memory-hygiene`](skills/agent-memory-hygiene/SKILL.md) | When and how to commit to a project memory system | Managing memory item quality, session boundaries, and retrieval accuracy |
| [`nono-usage`](skills/nono-usage/SKILL.md) | Setup nono for Claude Code: profile pack, shell wrapper, ad-hoc path grants, custom profiles | Setting up nono, adding project paths, diagnosing denied paths before a session starts |
| [`jira-ticket-workstream-overview`](skills/jira-ticket-workstream-overview/SKILL.md) | Cross-reference your Jira tickets against agent-memory workstreams; status, upcoming, blind spots | You want an overview of where your tickets stand vs your current focus areas |
| [`close-pr`](skills/close-pr/SKILL.md) | Author-side PR close: format/pre-commit, push, poll CI + approvals, merge (manual or auto-merge), branch cleanup, ticket transition, memory episode | You want to take a finished PR from "implementation done" to "merged + archived" |
| [`post-merge-validation`](skills/post-merge-validation/SKILL.md) | Poll the staged post-merge deploy pipeline, auto-approve dev gate only, run a Databricks task-count delta canary check when a DBX deploy is involved | You want to watch/validate a deployment after merging to main |
| [`search-coverage-reporting`](skills/search-coverage-reporting/SKILL.md) | Report what a search did *not* examine; classify depth vs breadth questions before answering | You are answering a code question by grep/glob/read, or auditing/mapping something where completeness is the deliverable |
| [`agent-implementation-gang`](skills/agent-implementation-gang/SKILL.md) | Bounded multi-agent delivery: roles and decision rights, one-owner-per-path, model capability tiers per role, code and test budget, append-only worklog with a resume checkpoint, read-only verification critic, worklog-vs-memory split | A project needs several agents, several sessions, human approvals, and evidence-based completion |
| [`tempo-worklog-cli`](skills/tempo-worklog-cli/SKILL.md) | Log or query Tempo Timesheets worklogs on Jira Cloud via API | You want to fill in hours, check logged time, or automate Tempo entries |
| [`c4-architecture-diagrams`](skills/c4-architecture-diagrams/SKILL.md) | C4 diagrams as PlantUML source: level/audience mapping, classification rules for the hard cases (managed cloud services, message buses, microservices, SPAs, libraries), repo layout by audience, shared `conventions.puml`, status tags for unbuilt architecture, per-level rot rate, diagramming vs modelling, review checklist, anti-patterns | You are writing or reviewing a C4 diagram, or setting up an architecture-as-code repo |
| [`text-writer`](skills/text-writer/SKILL.md) | Revise prose for classic style and reader working memory: curse-of-knowledge gaps, sentence mechanics, the five heavy-noun-phrase plagues (DeScioli & Pinker 2021), metadiscourse; a do-not-touch list for identifiers/errors/quotes, a hedging guard rail so style passes cannot assert unverified facts, and a fixed diagnosis/revision/before-after output contract | You are writing or revising a PR body, ticket, design doc, release note, or any prose a human reads, and it reads dense, abstract, or hedged |
| [`codebase-spec-reverse-engineering`](skills/codebase-spec-reverse-engineering/SKILL.md) | Perform a complete reverse-engineering analysis of a codebase to generate an exhaustive, implementation-ready Technical Specification Document for clean-room reimplementation | You need to reverse-engineer an existing repository into a zero-ambiguity, clean-room technical specification document covering domain invariants, schemas, state machines, math/algorithms, UI flows, and test fixtures |


## Plugins

Plugins add scripts and hooks on top of a skill. Install them from this
repository as a marketplace; each keeps its state under `~/.claude/<name>/`.

| Plugin | What it does | Use when |
|---|---|---|
| [`recent-tracker`](recent-tracker/) | Logs edited files and memory writes from a `PostToolUse` hook, split into design docs / code / memory notes | You want to see what you touched recently across projects |
| [`usage-stats`](usage-stats/) | Weekly report over your own Claude Code transcripts: time per topic, share of prompts that correct or redirect the assistant, and sessions that produced no file change | You want to know where your Claude Code time goes and which prompts cost you rounds |

`usage-stats` reads only the transcripts Claude Code already writes, so it needs
no hook. It calls a cheap model to name topics; run `classify.py --dry-run`
first to see the estimated cost.

## Plugins

Plugins add scripts and hooks on top of a skill. Install them from this
repository as a marketplace; each keeps its state under `~/.claude/<name>/`.

| Plugin | What it does | Use when |
|---|---|---|
| [`recent-tracker`](recent-tracker/) | Logs edited files and memory writes from a `PostToolUse` hook, split into design docs / code / memory notes | You want to see what you touched recently across projects |
| [`usage-stats`](usage-stats/) | Weekly report over your own Claude Code transcripts: time per topic, share of prompts that correct or redirect the assistant, and sessions that produced no file change | You want to know where your Claude Code time goes and which prompts cost you rounds |

`usage-stats` reads only the transcripts Claude Code already writes, so it needs
no hook. It calls a cheap model to name topics; run `classify.py --dry-run`
first to see the estimated cost.

## Contributing

- Keep skills focused on one job.
- Prefer generic examples and placeholders over internal names or IDs.
- Treat skill content as publishable documentation.
- Check the confidentiality boundary before committing changes.
