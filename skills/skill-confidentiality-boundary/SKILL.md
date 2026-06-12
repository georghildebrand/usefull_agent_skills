---
name: skill-confidentiality-boundary
description: Use when writing or reviewing skills to ensure no internal, confidential, or proprietary information is embedded
---

# Skill Confidentiality Boundary

## Overview

Skills are reusable across projects and contexts. **Never embed internal company data, credentials, or confidential information.** Skills become public references—treat them like published documentation.

## When to Use

**Before writing ANY skill:**
- Company names, product names (generalize: "example company", "SaaS platform")
- Ticket IDs, issue numbers (use placeholder: `<TICKET_ID>`)
- Employee names, roles, internal teams
- Internal URLs, workspace IDs, account numbers
- API keys, tokens, credentials (never, ever)
- Strategic information, roadmap details, business metrics
- Internal tooling, processes, workflows specific to one org
- Proprietary algorithms, custom implementations

**After writing a skill:**
- Search for proper nouns (company/product names) → generalize
- Search for numbers that look like IDs (job IDs, run IDs, etc.) → replace with placeholders
- Search for URLs with internal domains → replace with generic examples
- Ask: "Would this be safe to publish on Stack Overflow?"

## Core Principle

**Skills = Published Documentation**

Once written, a skill is discoverable across projects, shared with other agents, potentially open-sourced. Treat confidential information as FORBIDDEN.

### What's OK

✅ Generic examples: `example-job`, `my-database`, `workspace-url`
✅ Placeholder IDs: `<JOB_ID>`, `<RUN_ID>`, `<WORKSPACE_URL>`
✅ Public APIs: AWS SDK syntax, Databricks CLI commands, open libraries
✅ Best practices: Patterns, techniques, workflows applicable anywhere
✅ Anonymized lessons: "We found X in production" (no details identifying the company)

### What's NOT OK

❌ Company name: "At Acme Corp, we use..."
❌ Specific ticket: "ACME-1234 fixed by..."
❌ Employee mention: "John from DevOps reviewed..."
❌ Internal URL: "https://acme-internal.slack.com"
❌ Real workspace/account IDs: Actual AWS account numbers, Databricks workspace IDs
❌ Credentials of any kind: API keys, tokens, private keys
❌ Strategic info: "Our roadmap includes...", "Revenue impact was..."
❌ Internal tool names: Proprietary frameworks, internal CLIs, custom deployments

## Examples

### ❌ BAD: Embedded company context

```markdown
# Acme Corp Databricks Job Monitoring

When working on the demand forecaster (<TICKET_ID>), we needed to check job status.

**Workspace ID:** <WORKSPACE_ID>
**Account:** Acme AWS prod account (ID: <ACCOUNT_ID>)
**Team responsible:** Alice and Bob from the data team
```

### ✅ GOOD: Generalized, reusable

```markdown
# Databricks CLI Job Status Checker

When debugging job failures, you need to check run status and fetch logs.

**Setup:** Configure auth with workspace URL and token
**Authentication:** `databricks auth login --host <WORKSPACE_URL> --token <PAT_TOKEN>`
```

### ❌ BAD: Specific ticket leakage

```markdown
## Real-World Impact

**<TICKET_ID> incident:** Job cluster capacity errors were fixed by migrating to fleet instance types.
At <Company Name>, this saved 3 hours per week on debugging.
```

### ✅ GOOD: Anonymized lesson

```markdown
## Real-World Impact

**Symptom:** Job clusters fail with "not enough instances" under load.
**Solution:** Switch to fleet instance types for automatic Spot capacity optimization.
**Benefit:** Reduces manual debugging and improves reliability.
```

## Confidentiality Checklist (Before Committing)

- [ ] No company/product names (replace with "example", "my-app", etc.)
- [ ] No ticket IDs or issue numbers (use `<TICKET_ID>`)
- [ ] No employee names or internal roles mentioned
- [ ] No real workspace/account/job IDs (use `<ID>`, `<WORKSPACE_URL>`)
- [ ] No API keys, tokens, or credentials anywhere
- [ ] No internal URLs (use generic examples or `<INTERNAL_URL>`)
- [ ] No strategic/business information (roadmaps, metrics, revenue)
- [ ] No proprietary tool names or internal frameworks
- [ ] No specific dates/timelines that reveal business operations
- [ ] Examples use generic names (`job-123`, `user-data`, `forecast-output`)
- [ ] No internal profile names, workspace slugs, or note identifiers
- [ ] No hidden memory IDs, note keys, or other traceable internal IDs

**Red flag:** If you had to anonymize this before sharing with a colleague outside your company, remove it from the skill.

## Handling Real Examples

**Problem:** You want to share a concrete example, but it contains internal data.

**Solution:** Create a synthetic example that replicates the pattern without revealing secrets:

```markdown
# ❌ BAD: Real internal example with company context
databricks jobs get-run --run-id <REAL_RUN_ID> \
  --host https://<internal-company>.cloud.databricks.com \
  --token dapi123abc456xyz
```

```markdown
# ✅ GOOD: Synthetic example, same pattern
databricks jobs get-run --run-id <RUN_ID> \
  --host https://<WORKSPACE_URL> \
  --token <PAT_TOKEN>
```

## Public vs Private Skills

**Public skills (in shared repo):**
- MUST follow confidentiality boundary
- Assume audience includes strangers
- No internal context, no proprietary detail

**Private skills (in `~/.claude/skills/`):**
- Still should avoid embedding secrets
- Can reference internal processes (CLAUDE.md is better for this)
- Don't reference specific company data without strong reason

**Best practice:** Write all skills as if they'll go public. If information is too sensitive to publish, it doesn't belong in a skill—put it in CLAUDE.md (project-specific instructions) instead.

## When to Use CLAUDE.md Instead

**If you're writing about:**
- Internal process workflows (how YOUR team works)
- Project-specific conventions (ticket naming, code standards)
- Confidential business context (why this project exists)
- Internal tool configuration

**Then:** Put it in CLAUDE.md, not in a skill.

**Skills:** General techniques, patterns, tools applicable across projects
**CLAUDE.md:** Project context, internal workflows, confidential guidance

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| **Leaving real job IDs in examples** | Replace with `<JOB_ID>` placeholder |
| **Naming the company** | Use "example company" or remove entirely |
| **Referencing internal tickets** | Use `<TICKET_ID>` or describe symptom instead |
| **Mentioning employee names** | Generalize: "the team", "a developer", remove entirely |
| **Real workspace URLs** | Use `https://<WORKSPACE_URL>` or `https://workspace.cloud.databricks.com` |
| **Citing internal metrics** | Use relative terms: "improved performance", "reduced latency" |
| **Proprietary algorithm details** | Describe the pattern, not the implementation |

## Red Flags - STOP and Redact

If you find yourself writing ANY of these:
- Real account/workspace/job IDs
- Company or product names
- Employee names or titles
- Internal URLs or secrets
- Specific ticket numbers with context
- Business metrics or financial data
- Internal process workflows (unless generic pattern)

**Stop. Remove it. Rewrite generically.**

## Real-World Impact

**Before:** Skills embedded project context, leaked account IDs, exposed internal processes
**After:** Skills are reusable, safe to share, solve general problems for anyone

Skills become value over time only if they're portable. Confidential content reduces reusability and creates liability.
