---
name: databricks-cli
description: Use when interacting with Databricks from the command line, especially for job runs, cluster debugging, SQL queries, workspace assets, and deployment troubleshooting.
---

# Databricks CLI

## Overview

Databricks CLI covers terminal workflows: jobs, clusters, SQL, assets, auth. Two IDs matter most:

- `run_id`: one execution
- `job_id`: reusable template behind many runs

Wrong one → wrong result or wrong error.

## When To Use

- Job failed, need logs from terminal.
- Create/trigger job from script or CI pipeline.
- Quick SQL query without UI.
- Cluster/workspace metadata from CLI.

Prefer UI for visually complex job design or permission management.

## Core Concepts

### Run Vs Job ID

- `run_id`: single execution.
- `job_id`: reusable job definition.
- Run → job: inspect `jobs get-run` output, read `.job_id`.

### Authentication

```bash
# Interactive login
databricks auth login --host https://<WORKSPACE_URL> --token <PAT_TOKEN>

# Or env vars in CI/CD
export DATABRICKS_HOST=https://workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...

# Verify
databricks auth test
```

Auth fails → check token expiry, workspace URL, active profile correct. Multi-workspace: keep explicit profile, use consistently.

## Quick Reference Table

| Task | Command | Notes |
|------|---------|-------|
| Get run status | `databricks jobs get-run --run-id <RUN_ID>` | State, timing, and `state_message` |
| Get run logs | `databricks jobs get-run-output --run-id <RUN_ID>` | Stdout/stderr from tasks |
| Get job config | `databricks jobs get --job-id <JOB_ID>` | Cluster, tasks, schedule |
| List job runs | `databricks jobs list-runs --job-id <JOB_ID> --limit 10` | Recent executions |
| Create job | `databricks jobs create --json-file job.json` | From JSON config |
| Trigger run | `databricks jobs run-now --job-id <JOB_ID>` | Start job immediately |
| List clusters | `databricks clusters list --output json` | All clusters in workspace |
| Get cluster status | `databricks clusters get --cluster-id <CLUSTER_ID>` | Running, pending, terminated |
| Execute SQL | `databricks sql execute --statement "SELECT ..."` | v1.x only — absent in v1.2.x and older |
| List workspace assets | `databricks workspace list --path /` | Browse notebooks and files |
| Export notebook | `databricks workspace export --path /Users/me/notebook --format SOURCE --file-path ./notebook.py` | Handy for backup or review |

## Implementation: Common Workflows

### 1. Debugging A Failed Job

```bash
databricks jobs get-run --run-id <RUN_ID> --output json | jq '{state, state_message, start_time, end_time}'
databricks jobs get-run-output --run-id <RUN_ID> --output json | jq '.logs'
databricks jobs list-runs --job-id <JOB_ID> --limit 5 --output json | jq '.runs[] | {run_id, state, start_time, state_message}'
```

Check `state_message` first. Often names timeout, permission, or cluster problem.

### 2. Create and Trigger Job from CLI

```bash
# Create job from JSON config
databricks jobs create --json-file my-job.json

# Output: {"job_id": <JOB_ID>}

# Trigger it
databricks jobs run-now --job-id <JOB_ID>

# Output: {"run_id": <RUN_ID>}

# Monitor in real-time
databricks jobs get-run --run-id <RUN_ID> --output json | jq '.state'
```

**Minimal job JSON**
```json
{
  "name": "my-forecast-job",
  "new_cluster": {
    "spark_version": "15.4.x-scala2.12",
    "node_type_id": "m-fleet.2xlarge",
    "num_workers": 2
  },
  "spark_python_task": {
    "python_file": "dbfs:/scripts/forecast.py"
  }
}
```

### 3. Execute A SQL Query

`databricks sql execute` exists only in newer SDK-based CLI versions. Absent in v1.2.x and older. Use REST passthrough — works on any version:

```bash
# Via REST API (works on all CLI versions)
databricks api post /api/2.0/sql/statements \
  --profile <PROFILE> \
  --output json \
  --json '{
    "warehouse_id": "<WAREHOUSE_ID>",
    "statement": "SELECT COUNT(*) FROM my_table",
    "wait_timeout": "30s"
  }'
```

Results land in `.result.data_array` as JSON array of rows. Parse with:

```bash
databricks api post /api/2.0/sql/statements \
  --profile <PROFILE> \
  --output json \
  --json '{"warehouse_id":"<WAREHOUSE_ID>","statement":"SELECT * FROM my_table LIMIT 10","wait_timeout":"30s"}' \
  | python3 -c "import sys,json; [print(r) for r in json.load(sys.stdin)['result']['data_array']]"
```

If `databricks sql execute` IS available (newer CLI):

```bash
databricks sql execute --statement "SELECT COUNT(*) FROM my_table"
databricks sql execute --statement-path query.sql
```

### 4. Cluster Operations

```bash
# List clusters
databricks clusters list --output json | jq '.clusters[] | {cluster_id, cluster_name, state}'

# Get cluster details
databricks clusters get --cluster-id <CLUSTER_ID> --output json | jq '{spark_version, node_type_id, num_workers, state}'

# Start stopped cluster
databricks clusters start --cluster-id <CLUSTER_ID>

# Monitor startup
while true; do
  STATE=$(databricks clusters get --cluster-id <CLUSTER_ID> --output json | jq -r '.state')
  if [ "$STATE" = "RUNNING" ]; then
    echo "Cluster running"
    break
  fi
  echo "State: $STATE, waiting..."
  sleep 10
done
```

### 5. Browse Workspace Assets

```bash
# List workspace root
databricks workspace list --path /

# List specific folder
databricks workspace list --path /Users/me

# Get asset details (type, size, modified time)
databricks workspace get-status --path /Users/me/my-notebook

# Export notebook (useful for backup/CI)
databricks workspace export --path /Users/me/my-notebook --format SOURCE --file-path ./my-notebook.py
```

### 6. Chain Commands

```bash
# Get latest run ID for a job
LATEST_RUN=$(databricks jobs list-runs --job-id <JOB_ID> --limit 1 --output json | jq -r '.runs[0].run_id')

# Wait for completion
while true; do
  STATE=$(databricks jobs get-run --run-id $LATEST_RUN --output json | jq -r '.state')
  if [[ "$STATE" =~ ^(TERMINATED|SKIPPED|INTERNAL_ERROR)$ ]]; then
    echo "Run finished: $STATE"
    break
  fi
  echo "Still running: $STATE"
  sleep 5
done

# Check result
databricks jobs get-run --run-id $LATEST_RUN --output json | jq '.state_message'
```

## Version Compatibility

| CLI Version | Command Style | Notes |
|-------------|---|---|
| v0.x old releases | `databricks jobs get-run <RUN_ID>` (positional) | Avoid if possible |
| v1.x modern releases | `databricks jobs get-run --run-id <RUN_ID>` | Preferred form |
| v1.2.x and older | `databricks jobs delete <JOB_ID>` (positional) | `--job-id` flag does NOT exist |
| v1.x newer SDK | `databricks jobs delete --job-id <JOB_ID>` | Flag-based form |
| v1.2.x and older | `databricks sql execute` absent | Use `databricks api post /api/2.0/sql/statements` |

Same binary name, very different interfaces across installs. Flag rejected with `unknown flag` → check `databricks <subcommand> --help`; positional args won't appear as flags.

**Check version:**
```bash
databricks --version
```

Two CLI versions in PATH (e.g. Homebrew install + VS Code extension) conflict silently. `which -a databricks` reveals both.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Job ID where run ID is needed | Use `jobs list-runs` first, then inspect the run |
| Checking logs before `state_message` | Read `state_message` first |
| Forgetting `--output json` when parsing | Add `--output json` before piping to `jq` |
| Using the wrong cluster or job identifier | Stop and confirm whether you need a run, job, or cluster ID |
| Tight polling loops | Sleep between checks to avoid noisy API use |
| Hyphenated Unity Catalog table names | Use identifier-safe names; replace hyphens with underscores |
| Inconsistent artifact filenames | Include a version in the filename; Databricks caches by filename |

## Deployment Notes

- Keep `jobs get-run` (status) and `jobs get-run-output` (output) separate in your head.
- Bundles/deploy scripts: preserve same filename/version pair across runs so CLI does not reuse stale artifacts.
- Generated table names: normalize to lowercase underscore identifiers before sending to Databricks.

## Red Flags

**Commands indicating misunderstanding:**
- `databricks jobs get-run <RUN_ID>` when the installed CLI expects `--run-id`
- `databricks jobs get --run-id <RUN_ID>` (mixing job and run commands)
- `databricks jobs list-runs --run-id <RUN_ID>` (that flag expects a job ID)
- `databricks sql execute --path query.sql` (use `--statement-path`)

Wrote these → stop, check syntax via `databricks <command> --help`.
