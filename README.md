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

## Contributing

- Keep skills focused on one job.
- Prefer generic examples and placeholders over internal names or IDs.
- Treat skill content as publishable documentation.
- Check the confidentiality boundary before committing changes.
