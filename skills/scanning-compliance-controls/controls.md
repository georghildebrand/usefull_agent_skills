# Control catalog for scans

The common core of ISO/IEC 27001:2022 Annex A and the SOC 2 Trust Services
Criteria (TSC). The mapping columns are a common reading, not an official
crosswalk. The official AICPA mapping dates from 2018 and uses the 2013
Annex A numbers. Check numbers against the standard texts before you quote
them to an auditor.

Kinds of target: **C** code repo, **I** infrastructure as code, **A** live
cloud account, **D** documentation, **T** ticket or PR system.

| # | Control | ISO 27001:2022 | SOC 2 | Seen in | Signals to search |
|---|---|---|---|---|---|
| 1 | Security policy and roles | A.5.1, A.5.2 | CC1, CC2 | D | policy files, `SECURITY.md`, owner fields, "responsible" |
| 2 | Risk assessment, accepted risks | Clause 6.1, A.5.7 | CC3 | D, T | risk register, threat model per product, "accepted risk" tickets |
| 3 | Asset inventory | A.5.9 | CC6.1 | D, I, A | account or subscription list, service catalog, mandatory resource tags |
| 4 | Access control and least privilege | A.5.15, A.5.18, A.8.2 | CC6.1, CC6.3 | I, A, D | IAM or RBAC policies, wildcard actions, role definitions, break-glass rule |
| 5 | Authentication | A.5.17, A.8.5 | CC6.1 | I, A, D | SSO, MFA, no long-lived keys, OIDC in CI |
| 6 | Access review and leavers | A.5.18, A.6.5 | CC6.2, CC6.3 | T, D | review cadence with a number, review records, offboarding checklist |
| 7 | Secrets | A.5.17, A.8.24 | CC6.1 | C, I, D | secret manager use, rotation interval with a number, secret scanning in CI |
| 8 | Cryptography | A.8.24 | CC6.1, CC6.7 | I, A | encryption at rest, KMS keys, TLS settings |
| 9 | Change management | A.8.32 | CC8.1 | C, T, D | `CODEOWNERS`, branch protection, required approvals, approvals dismissed on new commits, change label on tickets |
| 10 | Segregation of duties | A.5.3 | CC5, CC8.1 | C, I, T | deploy only by CI, author cannot approve own PR, no local apply to production |
| 11 | Separate environments, test data | A.8.31, A.8.33 | CC8.1 | I, D | one account or subscription per stage, rule on customer data in non-production |
| 12 | Secure development and testing | A.8.25, A.8.28, A.8.29 | CC8.1 | C | tests in CI, linters, SAST, pre-commit hooks |
| 13 | Vulnerability and patch management | A.8.8 | CC7.1 | C, I, A, T | dependency update bot, image scan, remediation deadlines, patch tickets with versions |
| 14 | Configuration management, drift | A.8.9 | CC7.1 | I, A | pinned versions, remote state with locking, scheduled drift check |
| 15 | Logging and monitoring | A.8.15, A.8.16 | CC7.2 | I, A, D | log retention, audit log, alert routing to an owner, no secrets in logs |
| 16 | Incident management | A.5.24 to A.5.28 | CC7.3, CC7.4, CC7.5 | D, T | incident process with roles and deadlines, postmortems, exercise records |
| 17 | Backup and continuity | A.8.13, A.5.29, A.5.30 | A1.2, A1.3 | I, A, D | backup configuration, restore test records, RPO and RTO |
| 18 | Suppliers and cloud services | A.5.19 to A.5.23 | CC9.2 | D | supplier list with assessment, provider dependency list, contracts |
| 19 | Data handling and privacy | A.5.12, A.5.34, A.8.10, A.8.11 | C1.1, C1.2, P-series | D, I | data region, retention, deletion, masking in logs |
| 20 | Documented procedures | A.5.37, Clause 7.5 | CC2 | D | runbooks with owner, document history, review dates |
| 21 | Awareness and training | A.6.3 | CC1.4, CC2.2 | none of the above | usually not visible in a repo: mark "not visible here" |
| 22 | Internal audit, management review | Clause 9.2, 9.3 | CC4 | none of the above | usually not visible in a repo: mark "not visible here" |

## Tools that already map checks to frameworks

| Tool | Target | Command or note |
|---|---|---|
| Prowler | live AWS, Azure, GCP, Kubernetes, M365, GitHub | `prowler <provider> --list-compliance`, then `prowler <provider> --compliance <framework_id>` |
| Checkov | Terraform, CloudFormation, Kubernetes, Helm, ARM, Bicep | policy-as-code checks before deploy |
| trivy | images, IaC, dependencies | vulnerabilities and misconfigurations |
| Steampipe | cloud APIs through SQL | compliance mods; check which frameworks a mod covers |

## AI systems

For a platform that runs AI models or agents, ISO/IEC 42001 (AI management
system) uses the same clause structure as ISO 27001 and adds an AI system
impact assessment. Add it as a separate row group when the user asks about AI
governance. Do not map its controls one to one onto Annex A.
