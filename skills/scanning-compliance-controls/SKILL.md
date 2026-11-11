---
name: scanning-compliance-controls
description: Use when asked whether a repository, a folder of repositories, a cloud account or a set of documents is ready for ISO 27001, SOC 2 or a similar security audit, when asked for a control status table, a gap list or "what would an auditor find", or before an audit when time is short and a quick verdict is requested.
---

# Scanning compliance controls

## Overview

A scan finds evidence for controls. It never proves compliance. An audit judges
a management system and a period of operation. One repository holds only a
part of either.

**Core rule:** every row of the result names the kind of evidence found and
where it was found. "Not examined" is never reported as "missing".

## Three kinds of evidence

| Kind | What it is | Example | Enough for |
|---|---|---|---|
| Rule | A written requirement | "Production changes need one review" in a standards file | Policy documentation only |
| Implementation | Configuration that enforces the rule | `CODEOWNERS`, a branch-protection setting, an OIDC role in Terraform, a scan step in the CI file | ISO stage 1, SOC 2 Type I design |
| Operation | Records that the rule ran over time | Merged PRs with approvals, labelled change tickets, CI run history, an access-review record | SOC 2 Type II, ISO surveillance audits |

A rule without implementation is a gap. An implementation without operation
records is a gap for SOC 2 Type II.

## Procedure

1. **Name the target and its kind**: code, infrastructure as code, live cloud
   account, documentation, ticket system. Say which kinds are out of reach.
2. **Enumerate before reading.** List every candidate file first (standards,
   policies, CI files, IaC, `CODEOWNERS`, runbooks). Mark each one read or
   skipped. REQUIRED: follow `search-coverage-reporting` for breadth questions.
3. **Pick the controls** from [controls.md](controls.md) that this kind of
   target can show. Mark the rest "not visible here", for example training or
   physical security in a code repository.
4. **Search each control** with the signals in `controls.md`. Record the
   location as `path:line`.
5. **Assign one status** per control:
   - `operation`: operation records found
   - `implemented`: enforcing configuration found
   - `rule only`: written rule, nothing that enforces it
   - `absent`: every candidate source was read, nothing found
   - `not examined`: a source that could hold it was not read, or was blocked
   - `not visible here`: this kind of target cannot show it

   When the text points to a parent policy that was not read (for example a
   company ISMS), keep the status and write `inherited: <parent>` in the Gap
   column.
6. **Use existing scanners** for live accounts and IaC instead of judging
   configuration by hand: Prowler (`prowler <provider> --list-compliance`,
   then `--compliance <framework>`), Checkov or trivy for IaC. Report their
   result as a separate row, with the command used.
7. **Write the report** (format below).

## Report format

```
Scope: <targets>. Kinds covered: <...>. Kinds out of reach: <...>.

| Control | ISO 27001:2022 | SOC 2 | Status | Evidence (path:line) | Gap |

The table has these six columns in every report, also a short one. When
words are limited, shorten the Gap column to a few words.

What this scan cannot judge: <operation over time, parent policy, systems not reached>.
Coverage: read <n> of <m> candidate files: <list>. Not examined: <list, why>.
Next evidence to collect: <3-5 concrete items>.
```

No "compliant", "audit-ready" or "not audit-ready" verdict. If the user asks
for one, answer with the highest evidence kind reached, for example "rules
for 12 controls, implementation for 4, operation records for none in this
repository".

## Common mistakes

| Mistake | Fix |
|---|---|
| Marking a control `absent` after reading 3 of 8 standards files | Read every candidate, or mark it `not examined` |
| A verdict on audit readiness from one documentation repository | Report evidence kinds; name what the scan cannot see |
| Counting a written rule as a working control | Look for the configuration that enforces it |
| "Should" in a rule treated as "must" | Report it as a gap: auditors sample every environment in scope |
| Quoting an overlap percentage between ISO 27001 and SOC 2 | No official 2022 crosswalk exists; mappings in `controls.md` are a common reading |
| A file blocked by a hook or permission silently skipped | List it under "Not examined" with the reason |
