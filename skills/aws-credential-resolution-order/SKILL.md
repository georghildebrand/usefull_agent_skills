---
name: aws-credential-resolution-order
description: >
  Use when debugging AWS authentication issues, switching between named profiles
  and environment variables, or setting up multi-account workflows. Covers the
  silent override trap where env vars outrank AWS_PROFILE with no warning.
---

# AWS Credential Resolution Order

## The trap in one sentence

`AWS_PROFILE` silently ignored when `AWS_ACCESS_KEY_ID` set in env — SDK never
warns, you work against wrong account.

---

## Resolution order (highest → lowest priority)

1. **Explicit constructor args** — e.g. `boto3.Session(aws_access_key_id=...)`
2. **Environment variables** — `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` /
   `AWS_SESSION_TOKEN`
3. **AWS CLI config / credentials files** — `AWS_PROFILE` or `[default]`
4. **Container credential provider** — ECS task role, CodeBuild env
5. **EC2 instance metadata** — IMDSv2

SDK stops at first match. Env vars from previous shell session → profile-based
development invisible.

---

## The three scenarios

### Scenario A — env-only (CI/CD)

```bash
export AWS_ACCESS_KEY_ID=<key-id>
export AWS_SECRET_ACCESS_KEY=<secret>
export AWS_SESSION_TOKEN=<session-token>   # required for temp credentials
```

No `AWS_PROFILE` needed. SDK resolves to env vars. Validate:

```bash
aws sts get-caller-identity
```

### Scenario B — profile-only (local dev)

```bash
# Ensure no stale env vars from a previous session
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

export AWS_PROFILE=my-profile   # or: aws --profile my-profile <cmd>
aws sts get-caller-identity
```

Skip `unset` with stale env vars present → `AWS_PROFILE` overridden silently.
Caller identity shows wrong account.

### Scenario C — session token exported directly

User exports short-lived credentials directly into shell (common with SSO,
`aws-vault`, token-vending scripts):

```bash
export AWS_ACCESS_KEY_ID=<temp-key-id>
export AWS_SECRET_ACCESS_KEY=<temp-secret>
export AWS_SESSION_TOKEN=<temp-token>
```

**Do not** set `AWS_PROFILE` or unset these vars — env credentials intentional.
Validate only:

```bash
aws sts get-caller-identity
# Verify account ID and role/user ARN match what the user expects
```

---

## Diagnostic runbook

Run before any multi-account work or when auth behaves unexpectedly:

```bash
# 1. Check what env vars are set
env | grep -E "AWS_ACCESS_KEY|AWS_SECRET|AWS_SESSION_TOKEN|AWS_PROFILE|AWS_DEFAULT_REGION"

# 2. Resolve what the SDK actually uses
aws sts get-caller-identity

# 3. Compare account ID against what you expect
# If wrong account: check for stale env vars (step 1), then unset as needed
```

---

## Common mistakes

| Mistake | What happens | Fix |
|---|---|---|
| `AWS_PROFILE` set but `AWS_ACCESS_KEY_ID` also set | Profile silently ignored | `unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN` |
| Temp credentials without `AWS_SESSION_TOKEN` | Request signed with incomplete credentials; auth errors | Export all three vars together |
| Wrong region on multi-region setups | SDK uses wrong endpoint | See region section below |
| Assuming profile switch takes effect immediately in boto3 | boto3 sessions resolve credentials at construction time | New `boto3.Session()` after changing env vars |

---

## Region resolution (separate from credentials)

Region resolved independently, also in priority order:

1. Explicit `region_name` in constructor / `--region` flag
2. `AWS_DEFAULT_REGION` env var ← used by AWS CLI v1 and boto3
3. `AWS_REGION` env var ← used by AWS CLI v2 and Lambda runtime
4. Profile config `region =` in `~/.aws/config`

**SDK version split:** boto3 / AWS CLI v1 reads `AWS_DEFAULT_REGION`.
AWS CLI v2 reads `AWS_REGION` first. Set both if mixing v1 and v2 toolchains:

```bash
export AWS_DEFAULT_REGION=eu-west-1
export AWS_REGION=eu-west-1
```

---

## boto3 session timing gotcha

boto3 resolves credentials when session (or client/resource) created — not when
API call made. Changing env vars after session construction has no effect on
that session:

```python
import boto3, os

# Credentials resolved here — env vars locked in
session = boto3.Session()

os.environ["AWS_PROFILE"] = "other-profile"  # Too late — session already resolved

# To pick up new credentials, create a new session:
session2 = boto3.Session()
```

---

## Quick reference

```bash
# Always validate before any multi-account work
aws sts get-caller-identity

# Switch to a named profile cleanly
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
export AWS_PROFILE=<profile-name>
aws sts get-caller-identity   # verify

# Check all active credential env vars
env | grep AWS_
```
