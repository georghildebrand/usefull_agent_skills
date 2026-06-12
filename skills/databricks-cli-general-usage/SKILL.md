---
name: databricks-cli
description: Use when interacting with Databricks from the command line, especially for job runs, cluster debugging, SQL queries, workspace assets, and deployment troubleshooting.
---

# Databricks CLI

## Overview

Databricks CLI covers the common terminal workflows: jobs, clusters, SQL, assets, and auth. The two IDs that matter most are:

- `run_id`: one execution
- `job_id`: the reusable template behind many runs

If you use the wrong one, you will usually get the wrong result or the wrong error.

## When To Use

- Job failed and you need logs from the terminal.
- You want to create or trigger a job from a script or CI pipeline.
- You need a quick SQL query without opening the UI.
- You want cluster or workspace metadata from the CLI.

Prefer the UI for visually complex job design or permission management.

## Core Concepts

### Run Vs Job ID

- `run_id` identifies a single execution.
- `job_id` identifies the reusable job definition.
- To move from run to job, inspect `jobs get-run` output and read `.job_id`.

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

If auth fails, check token expiry, workspace URL, and whether the active profile is the one you intended. In multi-workspace setups, keep an explicit profile and use it consistently.

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
| Execute SQL | `databricks sql execute --statement "SELECT ..."` | Direct query execution |
| List workspace assets | `databricks workspace list --path /` | Browse notebooks and files |
| Export notebook | `databricks workspace export --path /Users/me/notebook --format SOURCE --file-path ./notebook.py` | Handy for backup or review |

## Implementation: Common Workflows

### 1. Debugging A Failed Job

```bash
databricks jobs get-run --run-id <RUN_ID> --output json | jq '{state, state_message, start_time, end_time}'
databricks jobs get-run-output --run-id <RUN_ID> --output json | jq '.logs'
databricks jobs list-runs --job-id <JOB_ID> --limit 5 --output json | jq '.runs[] | {run_id, state, start_time, state_message}'
```

Check `state_message` first. It often already names the timeout, permission, or cluster problem.

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

```bash
# Single statement
databricks sql execute --statement "SELECT COUNT(*) FROM my_table"

# From file
databricks sql execute --statement-path query.sql

# With output formatting
databricks sql execute --statement "SELECT * FROM my_table LIMIT 10" --output json | jq '.[] | {col1, col2}'
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
| Old releases | `databricks jobs get-run <RUN_ID>` (positional) | Avoid if possible |
| Modern releases | `databricks jobs get-run --run-id <RUN_ID>` | Preferred form |

**Check version:**
```bash
databricks --version
```

If syntax and output disagree with this file, check the installed CLI version before assuming the command is wrong.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Job ID where run ID is needed | Use `jobs list-runs` first, then inspect the run |
| Checking logs before `state_message` | Read `state_message` first |
| Forgetting `--output json` when parsing | Add `--output json` before piping to `jq` |
| Using the wrong cluster or job identifier | Stop and confirm whether you need a run, job, or cluster ID |
| Tight polling loops | Sleep between checks to avoid noisy API usage |
| Hyphenated Unity Catalog table names | Use identifier-safe names; replace hyphens with underscores |
| Inconsistent artifact filenames | Include a version in the filename; Databricks caches by filename |

## Deployment Notes

- Keep `jobs get-run` and `jobs get-run-output` separate in your head: one is status, the other is output.
- If you create bundles or deploy scripts, preserve the same filename/version pair across runs so the CLI does not reuse stale artifacts.
- For generated table names, normalize to lowercase underscore identifiers before sending them to Databricks.

## Red Flags

**Commands indicating misunderstanding:**
- `databricks jobs get-run <RUN_ID>` when the installed CLI expects `--run-id`
- `databricks jobs get --run-id <RUN_ID>` (mixing job and run commands)
- `databricks jobs list-runs --run-id <RUN_ID>` (that flag expects a job ID)
- `databricks sql execute --path query.sql` (use `--statement-path`)

If you write these, stop and check syntax via `databricks <command> --help`.
