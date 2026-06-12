---
name: atlassian-cli-setup
description: >
  Use for initial setup of atlassian-cli: profile creation, auth login flags,
  token sourcing, base URLs, default profile selection, and auth troubleshooting.
  For runtime usage (issue updates, PR creation, ADF richtext, cross-profile
  workflows), see the companion skill `atlassian-cli-usage`.
---

# atlassian-cli — Jira, Confluence, Bitbucket

`atlassian-cli` is a Rust-based CLI for Jira, Confluence, and Bitbucket.
Install via `brew install atlassian-cli`.

## Profile Overview

| Profile | Site | Use for |
|---------|------|---------|
| `<jira-profile>` (often default) | `https://<org>.atlassian.net/` | Jira + Confluence |
| `<bitbucket-profile>` | `https://<org2>.atlassian.net/` or a separate Bitbucket org | Bitbucket |

Always put `--profile <name>` **before** the subcommand:
```bash
atlassian-cli --profile <name> jira issue get PROJ-123
```

---

> For cross-profile workflows after setup, see `atlassian-cli-usage`.

---

## Setup Flow

1. Create or confirm the profile you want for Jira/Confluence.
2. Create a separate profile for Bitbucket if it lives in a different org.
3. Keep the profiles explicit. Do not rely on silent default fallbacks.

For Bitbucket login, use the Bitbucket-specific flag and verify with `bitbucket whoami`:

```bash
atlassian-cli --profile <bitbucket-profile> auth login --bitbucket --bearer --token <TOKEN>
atlassian-cli --profile <bitbucket-profile> bitbucket whoami
```

If a Bitbucket login seems to have affected Jira access, re-run the Jira login for the Jira profile.

## Jira Basics

```bash
# Read
atlassian-cli --profile <p> jira issue get PROJ-123
atlassian-cli --profile <p> jira issue search --jql "project = PROJ AND status = 'In Progress'"
atlassian-cli --profile <p> jira issue search --jql "project = PROJ AND parent = PROJ-68 ORDER BY created ASC"

# Create
atlassian-cli --profile <p> jira issue create \
  --project PROJ \
  --issue-type "Story" \
  --summary "..." \
  --description "..."

# Create sub-task under a story
atlassian-cli --profile <p> jira issue create \
  --project PROJ \
  --issue-type "Sub-task" \
  --summary "..." \
  --description "..." \
  --field 'parent={"key":"PROJ-123"}'

# Create story under an epic
atlassian-cli --profile <p> jira issue create \
  --project PROJ \
  --issue-type "Story" \
  --summary "..." \
  --field 'parent={"key":"PROJ-68"}'

# Update
atlassian-cli --profile <p> jira issue update PROJ-123 --summary "New title"
atlassian-cli --profile <p> jira issue update PROJ-123 --description "Updated desc"

# Transition / assign
atlassian-cli --profile <p> jira issue transition PROJ-123 --status "In Progress"
atlassian-cli --profile <p> jira issue assign PROJ-123 --assignee user@email.com
```

### Jira Hierarchy Rules
- Epic → Story: `--field 'parent={"key":"EPIC-KEY"}'`
- Story → Sub-task: `--field 'parent={"key":"STORY-KEY"}'` + `--issue-type "Sub-task"`
- `customfield_10014` (Epic Link) is screen-gated in many instances — do not use it

---

## Confluence Basics

```bash
# Read — PAGE_ID is positional (no --id flag)
atlassian-cli --profile <p> confluence page get <PAGE_ID>

# Create page (body = Confluence Storage Format XHTML, must be file path)
atlassian-cli --profile <p> confluence page create \
  --space <SPACE_ID> \
  --title "..." \
  --body page.html \
  --parent <PARENT_PAGE_ID>

# Update
atlassian-cli --profile <p> confluence page update <PAGE_ID> \
  --title "..." \
  --body page.html
```

> `--body` takes a **file path**, not an inline string.  
> Content must be [Confluence Storage Format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html) (XHTML with `<ac:structured-macro>` etc.)

---

## Bitbucket Basics

```bash
# Who am I
atlassian-cli --profile <bb-p> bitbucket whoami

# Repos
atlassian-cli --profile <bb-p> bitbucket repo get --workspace <WORKSPACE> <REPO>

# Create PR
atlassian-cli --profile <bb-p> bitbucket pr create <REPO_SLUG> \
  --workspace <WORKSPACE_SLUG> \
  --source <feature-branch> \
  --destination main \
  --title "..." \
  --description "..."

# List / get PRs
atlassian-cli --profile <bb-p> bitbucket pr list --workspace <WORKSPACE> --repo <REPO>
atlassian-cli --profile <bb-p> bitbucket pr get <PR_ID> --workspace <WORKSPACE> --repo <REPO>

# Approve / merge
atlassian-cli --profile <bb-p> bitbucket pr approve <PR_ID> --workspace <WORKSPACE> --repo <REPO>
atlassian-cli --profile <bb-p> bitbucket pr merge <PR_ID> --workspace <WORKSPACE> --repo <REPO>
```

---

## Bitbucket Auth Setup

1. Create a Bitbucket token from the Atlassian account security page.
   - Use the Bitbucket-scoped token option if the account offers one.
   - Include read and pull request write scopes.

2. Login:
   ```bash
   atlassian-cli --profile <bb-profile> auth login --bitbucket --bearer --token <TOKEN>
   ```

3. Verify:
   ```bash
   atlassian-cli --profile <bb-profile> bitbucket whoami
   ```

### Jira/Confluence Auth
```bash
atlassian-cli auth login --profile <primary-profile> \
  --email <email> \
  --token <ATLASSIAN_API_TOKEN> \
  --base-url https://<org>.atlassian.net/
```
Use the Jira/Confluence token flow for the Jira profile, and keep it separate from the Bitbucket login.

---

## Known Quirks

| Bug | Symptom | Workaround |
|-----|---------|------------|
| `auth list` looks fine but commands still fail | Profile selection or token scope is wrong | Use the target service command itself, like `bitbucket whoami` |
| `auth login --bitbucket` appears to affect the wrong profile | Default profile or stale config is being used | Re-run login with an explicit `--profile` and verify immediately |
| `jira issue delete` reports a parse error after success | Jira returns `204 No Content` | Verify with `issue get` instead of trusting exit text |

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Authentication failed` | Wrong token or email for Bitbucket account | Re-login with correct Bitbucket account email |
| `Resource not found` (404 on known repo) | Token missing `Repositories: Read` | Recreate token with correct scopes |
| `No Bitbucket token found` | Login ran without the Bitbucket flag | Re-run with `--bitbucket` |
| `credentials lack required privilege scopes` | Missing pull request write scope | Recreate the Bitbucket token with write scope |
| Jira behaves oddly after Bitbucket login | The active profile is not the Jira profile | Re-run Jira login for the Jira profile |
