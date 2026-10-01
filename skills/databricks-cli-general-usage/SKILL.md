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
| Cancel run | `databricks jobs cancel-run <RUN_ID>` | Async — echoes run object, must re-poll to confirm |
| List clusters | `databricks clusters list --output json` | All clusters in workspace |
| Get cluster status | `databricks clusters get --cluster-id <CLUSTER_ID>` | Running, pending, terminated |
| Execute SQL | `databricks sql execute --statement "SELECT ..."` | v1.x only — absent in v1.2.x and older |
| Execute SQL (newer builds) | `databricks experimental aitools tools query "SELECT ..." --output json` | Picks a warehouse; rows as JSON list |
| Rerun one task | `databricks jobs run-now --json '{"job_id": <JOB_ID>, "only": ["<TASK_KEY>"]}'` | Other tasks show `DISABLED` |
| Active runs | `databricks jobs list-runs --active-only --output json` | Lists all users' runs; filter by job ID |
| Job cost | `system.billing.usage` × `system.billing.list_prices` | See section 8; billing lags hours |
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

### 7. Cancel A Running Run

`cancel-run` is **asynchronous**: it echoes the full run object (large — pipe or discard) and returns before teardown finishes. Always re-poll `get-run` to confirm the terminal state.

```bash
# Fire cancel (drop the echoed run object)
databricks jobs cancel-run <RUN_ID> --output json > /dev/null

# Confirm it actually cancelled
databricks jobs get-run <RUN_ID> --output json | jq '{
  life_cycle_state: .state.life_cycle_state,
  result_state:     .state.result_state,
  user_cancelled:   .state.user_cancelled_or_timedout,
  state_message:    .state.state_message
}'
# Cancelled → life_cycle_state=TERMINATED, result_state=CANCELED, user_cancelled=true
```

Two state fields, distinct meaning: `life_cycle_state` = lifecycle phase (RUNNING→TERMINATED); `result_state` = outcome (CANCELED/FAILED/SUCCESS). A cancel is confirmed by both, plus `user_cancelled_or_timedout=true`.

### 8. Estimate What Job Runs Cost

The system billing tables hold usage in DBUs (Databricks Units) per job run, and the list price per DBU. Query them with any SQL route (section 3, or `experimental aitools tools query` below).

```sql
-- 1. List price of the SKU your runs use (serverless SKUs differ per cloud region)
SELECT sku_name, pricing.default AS price_per_dbu, currency_code, price_start_time, price_end_time
FROM system.billing.list_prices
WHERE sku_name = '<SKU_NAME>'            -- e.g. PREMIUM_JOBS_SERVERLESS_COMPUTE_<REGION>
ORDER BY price_start_time DESC
LIMIT 5;

-- 2. DBUs and list cost per job run, joined to the price valid at usage time
SELECT u.usage_metadata.job_id, u.usage_metadata.job_run_id, min(u.usage_date) AS day, u.sku_name,
       ROUND(SUM(u.usage_quantity), 4) AS dbus,
       ROUND(SUM(u.usage_quantity * p.pricing.default), 4) AS list_cost
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
 AND u.usage_start_time >= p.price_start_time
 AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_metadata.job_id IN ('<JOB_ID_1>', '<JOB_ID_2>')
GROUP BY 1, 2, 4
ORDER BY 1, 3, 2;
```

Rules for reading the result:

- **Billing lags.** Rows arrive hours after a run ends. For today's runs, estimate: DBU per task-minute of already-billed runs × task-minutes of the new run (task-minutes = sum of `execution_duration` of the tasks from `jobs get-run`).
- **List price, not contract price.** `list_prices` holds public list prices; a negotiated discount is not in these tables.
- **Only job compute.** SQL warehouse queries that you ran to explore data bill under a warehouse SKU and have no `job_id`; query them separately if they matter.
- **Parse the join window correctly.** Join on `usage_start_time`, not on `usage_date` alone, or a price change inside a day double-counts.

### 9. Lessons From Running Serverless Jobs

| Situation | What happens | Do this |
|-----------|--------------|---------|
| Several dataset tasks in parallel in one job run | They can share one serverless compute; each task gets slower (seen: ~2.7× longer model fits) | Chain the tasks with `depends_on` + `run_if: ALL_DONE`, or start separate job runs |
| Chained tasks under one job | Job-level `timeout_seconds` covers the whole run; tasks add up and the last one is killed with `TIMEDOUT` | Set the job timeout to the sum of task budgets; keep a per-task `timeout_seconds` too |
| Rerun one task of a multi-task job | — | `databricks jobs run-now --json '{"job_id": <JOB_ID>, "only": ["<TASK_KEY>"]}'`; skipped tasks show `DISABLED` |
| Logs of a multi-task run | `get-run-output` on the parent run ID fails | Take each task's `run_id` from `jobs get-run` → `.tasks[]`, then `get-run-output <TASK_RUN_ID>` |
| Two tasks write the same new table at the same time | `CREATE TABLE IF NOT EXISTS` race | A small setup task creates schema and tables first; data tasks depend on it |
| What runs right now? | `list-runs --active-only` lists every user's runs in the workspace | Filter by your job IDs before reporting |
| Upload a script for `spark_python_task` | A notebook import breaks the task | `databricks workspace import <PATH> --file <LOCAL> --format AUTO --language PYTHON --overwrite` imports it as a FILE |
| Script imports a sibling module from its own folder | `spark_python_task` runs the file through `exec()`: `__file__` is not defined → `NameError` at import | Take the folder from `sys.argv[0]` inside `try/except NameError`, and also add the known workspace folder to `sys.path` |
| Serverless task needs a wheel plus a PyPI package | — | Environment `spec.dependencies`: `["/Workspace/<DIR>/<WHEEL>.whl", "<package>==<version>"]`, `environment_version` pinned |

For ad-hoc SQL, newer CLI builds also offer `databricks experimental aitools tools query "<SQL>" --output json`; it picks a warehouse for you and returns rows as a JSON list.

## Version Compatibility

| CLI Version | Command Style | Notes |
|-------------|---|---|
| v0.x old releases | `databricks jobs get-run <RUN_ID>` (positional) | Avoid if possible |
| v1.x modern releases | `databricks jobs get-run --run-id <RUN_ID>` | Preferred form |
| v1.2.x and older | `databricks jobs delete <JOB_ID>` (positional) | `--job-id` flag does NOT exist |
| v1.2.x and older | `databricks jobs cancel-run <RUN_ID>` (positional) | `--run-id` flag does NOT exist |
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
