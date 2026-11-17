# Tile: jira

Document: `jira/open`.

## Source

Read-only. From the preset it needs `sources.jira` (project keys) and the CLI profile
(`sources.jiraProfile`, or the default profile). Both live in the private file.

```
atlassian-cli --profile <profile> jira api /rest/api/3/myself --output <scratchpad>/myself.json
atlassian-cli --profile <profile> jira api /rest/api/3/search/jql \
  --query 'jql=project in (<keys>) AND statusCategory != Done AND (assignee = currentUser() OR reporter = currentUser()) ORDER BY updated DESC' \
  --query maxResults=100 \
  --query 'fields=summary,status,issuetype,priority,updated,created,assignee,reporter,project,parent' \
  --output <scratchpad>/jira-search.json
```

## Build

`build_jira.build(issues, my_account_id, base_url, scope)` maps issues to items. It has no command line, so call it from Python:

```
python3 -c "import sys,json; sys.path.insert(0,'skills/dashboard/scripts'); import build_jira, common; \
s=json.load(open('<scratchpad>/jira-search.json')); me=json.load(open('<scratchpad>/myself.json')); \
common.write_json('<scratchpad>/jira-open.json', build_jira.build(s['issues'], me['accountId'], '<site base url>', '<keys>'))"
```

`<site base url>` is the profile's site address. It goes only into the document, never into the repo. Write the output with `ArtifactData` `set` to `jira/open`, with `if_version`.

## Left out

Descriptions, comments, assignee names, attachments.
