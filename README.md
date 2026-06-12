# usefull_agent_skills

Reusable Claude Code skills collection. Each skill lives in `skills/<name>/SKILL.md` and is discoverable through the Claude Code `Skill` tool.

## Skills

| Skill | What it covers | Use when |
|---|---|---|
| [`atlassian-cli-setup`](skills/atlassian-cli-setup/SKILL.md) | Initial auth, profile setup, and recovery | You are first setting up `atlassian-cli` or fixing auth |
| [`atlassian-cli-usage`](skills/atlassian-cli-usage/SKILL.md) | Jira, Confluence, and Bitbucket runtime usage | You need to update issues, create PRs, or write ADF content |
| [`databricks-cli`](skills/databricks-cli-general-usage/SKILL.md) | Databricks CLI operations and debugging | You need job runs, SQL, clusters, or workspace assets from the terminal |
| [`repo2ai`](skills/repo2ai/SKILL.md) | Export a repository as structured Markdown context | You want to load a whole repo into context for review or analysis |
| [`skill-confidentiality-boundary`](skills/skill-confidentiality-boundary/SKILL.md) | Keep skills generic and publish-safe | You are writing or reviewing a skill |
| [`aws-credential-resolution-order`](skills/aws-credential-resolution-order/SKILL.md) | AWS credential chain, silent env-var override, region split | Debugging "wrong account" auth or switching between profiles and session tokens |
| [`claude-code-unattended-bash`](skills/claude-code-unattended-bash/SKILL.md) | Three Bash patterns that block unattended sessions on approval prompts | Writing Bash for overnight jobs, background agents, or `/loop` polling |
| [`cross-repo-epic-review`](skills/cross-repo-epic-review/SKILL.md) | Four-round review structure for multi-repo epics | Reviewing a cross-team epic or deciding whether to split a phased epic |
| [`agent-memory-hygiene`](skills/agent-memory-hygiene/SKILL.md) | When and how to commit to a project memory system | Managing memory item quality, session boundaries, and retrieval accuracy |

## Contributing

- Keep skills focused on one job.
- Prefer generic examples and placeholders over internal names or IDs.
- Treat skill content as publishable documentation.
- Check the confidentiality boundary before committing changes.
