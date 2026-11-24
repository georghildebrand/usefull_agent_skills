# CoSAI MCP threat catalog

Condensed from the CoSAI paper "Model Context Protocol (MCP) Security", Workstream 4
(Secure Design Patterns for Agentic Systems), approved 8 January 2026. Written in our own
words, as a lookup table for reviews. Source and license notice at the end.

The paper covers the MCP specification 2025-06-18 and later revisions. It is guidance, not a
standard, and its own status is "Draft".

## Contents

1. Three tiers of threats
2. The twelve categories (MCP-T1 to MCP-T12) with threats and controls
3. The 34 numbered threats
4. Controls in detail (paper section 3.2)
5. Transport controls table
6. Deployment patterns
7. Incidents the paper cites
8. Source and license

## 1. Three tiers of threats

| Tier | Meaning | Threat numbers |
|---|---|---|
| 1 - MCP specific | New, caused by the design of MCP | 1-7 |
| 2 - MCP contextualized | Known threats that look different or are worse with MCP | 8-15 |
| 3 - Conventional | Classic security threats in the MCP stack | 16-34 |

## 2. The twelve categories

| ID | Category | Threats (numbers from section 3) | Controls (section 4) |
|---|---|---|---|
| MCP-T1 | Improper authentication and identity management | 1, 8, 16, 17, 18, 19 | Agent identity; secure delegation (OAuth) |
| MCP-T2 | Missing or improper access control | 8, 9, 10, 20 | Secure delegation; access control |
| MCP-T3 | Input validation and sanitization failures | 21, 22, 23 | Data sanitization; guardrails; sandboxing and isolation (MCP roots) |
| MCP-T4 | Data/instruction boundary failure (prompt injection class) | 2, 3, 4, 11, 21 | Input sanitization; guardrails; context isolation |
| MCP-T5 | Inadequate data protection and confidentiality | 22, 24 | Sandboxing and isolation; access control; guardrails; TEE |
| MCP-T6 | Missing integrity and verification controls | 4, 5, 6, 25 | Cryptographic integrity; remote attestation; server integrity |
| MCP-T7 | Session and transport security failures | 12, 23, 26, 27, 28, 29, 30 | Network and transport security |
| MCP-T8 | Network binding and isolation failures | 6, 10, 26, 31, 32 | Network and transport security; sandboxing and isolation |
| MCP-T9 | Trust boundary and privilege design failures | 7, 13 | Secure tool and UX design |
| MCP-T10 | No resource management or rate limits | 14, 33 | Network and transport security (payload limits, quotas) |
| MCP-T11 | Supply chain and lifecycle failures | 6, 25 | Lifecycle and governance |
| MCP-T12 | Insufficient logging, monitoring, auditability | 15, 34 | Logging; lifecycle and governance |

What each category means in practice:

- **T1** - The protocol makes authentication optional. MCP servers often hold many service
  credentials (OAuth tokens, API keys, database passwords) in one place, often unencrypted
  and never rotated. Result: impersonation, replay, token theft, confused deputy (a server
  that uses its own or another user's rights on behalf of a caller who should not have them).
- **T2** - No native fine-grained authorization in the protocol. Servers ask for broad scopes
  "for flexibility" and do not check per-object permissions. Result: broken object level
  authorization (BOLA, user A reads user B's record by changing an id), privilege
  escalation, cross-tenant data exposure.
- **T3** - Classic injection: command, SQL, LDAP, XML, path traversal, unsafe
  deserialization. Made worse by the false belief that input which passed through an LLM is
  safe. The LLM changes the payload's form; it does not clean it.
- **T4** - An LLM cannot tell instructions apart from data in its context. Any text an
  attacker can influence (tool descriptions, schemas, tool results, documents, emails, API
  responses) can change what the agent does next. Reading a document can lead to data
  exfiltration. Includes hidden Unicode instructions.
- **T5** - Personal data, financial data and intellectual property pass through without
  encryption, classification or segmentation. One protocol layer that reaches many services
  lets an attacker with partial access combine data across them. Leaks via logs, error
  messages, debug output.
- **T6** - No code signing, no message authentication, no tamper-evident logs. Tool
  definitions or configuration can change after approval ("rug pull"), tools can shadow
  other tools or copy their names.
- **T7** - Session ids sent insecurely, sessions not bound to a client, weak timeouts, TLS not
  enforced. Result: session hijacking, fixation, replay, man-in-the-middle, CSRF.
- **T8** - Servers bind to `0.0.0.0` instead of `127.0.0.1`, no network segmentation, no
  CORS policy, DNS rebinding possible (a web page in the user's browser reaches a local
  HTTP MCP server). Result: internal services exposed, lateral movement.
- **T9** - The protocol assumes client, server and downstream API trust each other. One
  compromised part breaks the whole chain. Includes over-reliance on the LLM and on human
  approval.
- **T10** - No limits on tokens, context size, call counts or cost. Result: denial of
  service and "denial of wallet" (an attacker makes the victim pay for many LLM calls).
- **T11** - Servers installed from public registries without checks, never inventoried,
  never retired. Shadow servers (installed without approval) and zombie servers
  (deprecated but still running); typosquatted package names.
- **T12** - No log of which tool was called, with which parameters, because of which prompt,
  under which authorization. No forensics, no compliance evidence.

## 3. The 34 numbered threats

The paper numbers threats 1-34. The numbers are its own; keep them when you cite.

Tier 1 - MCP specific:

1. **Identity spoofing** - weak auth lets an attacker act as a client or as the agent of a user.
2. **Tool poisoning** - malicious tool metadata delivered via `tools/list`. The MCP spec itself
   says tool annotations are untrusted unless the server is trusted.
3. **Full schema poisoning** - the whole tool schema is altered: hidden parameters, changed
   return types, malicious default values. Looks compatible, so monitoring misses it.
4. **Resource content poisoning** - instructions hidden in data the server fetches (database
   rows, documents, API responses). A persistent prompt injection through a trusted data
   channel. Grows with chained MCP server calls.
5. **Typosquatting / confusion** - servers or tools with names close to real ones; the LLM
   or the user picks the wrong one.
6. **Shadow MCP servers** - unapproved or unmonitored servers.
7. **Overreliance on the LLM** - the server exposes a powerful tool and trusts the model to
   call it correctly. Model refusals can be bypassed, and the model can be replaced by a
   weaker one.

Tier 2 - MCP contextualized:

8. **Privilege escalation via auth bypass** - including confused deputy when the server is
   an OAuth proxy that does not check whose authorization it uses.
9. **Insecure human-in-the-loop** - risky actions without user consent.
10. **Improper multitenancy** - tenants share memory, sessions, secrets or data.
11. **Prompt injection** - direct (also via sampling, or an LLM inside the tool) or indirect
    (via prompts, resources, tool metadata). Exists whenever untrusted input reaches the
    context window.
12. **Man-in-the-middle** - no TLS, bad certificate checks, no mutual auth.
13. **Consent fatigue** - so many approval prompts that users approve without reading.
14. **Resource exhaustion and denial of wallet.**
15. **Invisible agent activity** - agents or servers act covertly inside valid-looking workflows.

Tier 3 - conventional:

16. Credential / token theft
17. Replay attacks / session hijacking
18. OAuth or legacy auth weaknesses (basic auth, static API keys, token pass-through)
19. Session token leakage
20. Excessive permissions / overexposure
21. Command injection
22. File system exposure / path traversal
23. Insufficient integrity checks on messages and responses
24. Data exfiltration and corruption
25. Supply chain compromise
26. Unrestricted network access (inbound or outbound)
27. Protocol security gaps (no payload limits, no TLS, unauthenticated requests)
28. Insecure descriptor handling (stdio stream hijacking via inherited file descriptors)
29. Missing CSRF protection on HTTP transports
30. CORS / origin policy bypass
31. Malicious command execution by a rogue server
32. Dependency / update attack (rug pull; new unvetted tools appear after approval)
33. Payload limit / DoS (size or recursion depth)
34. Lack of observability

## 4. Controls in detail

**Agent identity (T1).** Every request must be traceable along the whole chain: end user or
initiating agent, every intermediate MCP server, the tool or service that acted. Workload
identity standards such as SPIFFE/SPIRE give cryptographic identities; the SPIFFE id can be the
subject or actor in a token exchange.

**Secure delegation and access control (T1, T2).**

- Authenticate users through an existing identity provider (OIDC).
- Register the MCP server as an OAuth client with the identity provider; if that cannot
  happen in advance, use Dynamic Client Registration.
- Never pass the user's OAuth token through to downstream services.
- Use token exchange (RFC 8693) so every downstream call is attributable.
- Reduce scopes to what the tool needs, for example no write scope for a read tool. The
  2025-11-25 MCP spec adds native scope definitions (SEP-835).
- Short-lived tokens; proof-of-possession with DPoP (RFC 9449) against replay.
- Rich Authorization Requests (RFC 9396) to limit a token to specific resources or tool
  parameters.
- Every endpoint enforces RBAC or ABAC against identity-provider claims. Policy engines:
  OPA, Cedar, OpenFGA.

**Input and data sanitization (T3, T4).**

- Allowlist validation at every trust boundary.
- Canonicalize file paths before checking them.
- Parameterized database queries.
- Output encoding for the target context (SQL, shell, HTML).
- Treat all AI-generated content as untrusted, like direct user input.
- Treat everything a server returns as untrusted: tool and resource definitions, resources,
  prompts, elicitation requests, tool responses.
- Prompt injection detection; strict JSON schemas to keep instructions and data apart.
- Optionally message authentication codes or signatures on tools and resources.

**Cryptographic integrity and remote attestation (T5, T6, T9).** Hardware trusted execution
environments (TEE: Intel TDX, AMD SEV-SNP) and confidential containers protect clients and
servers from the host operator, from co-tenants and from runtime tampering. With remote
attestation, a client can refuse a server whose measurements do not match, and secrets are only
released to attested servers. TEEs do not fix bugs in the running code; add seccomp, AppArmor
and similar runtime controls. Physical attacks are out of reach of TEEs.

**Sandboxing and isolation (T3, T5, T8).** Run agents and servers with least privilege. A
server that touches files, runs commands, opens network connections or executes LLM-generated
code must run in a sandbox. A plain container is not a strong security boundary; consider
gVisor, Kata Containers, SELinux sandboxes.

**Cryptographic verification of resources (T6, T11).** Server authors publish signatures and
an SBOM (software bill of materials). Deployers verify both before deployment and restrict
approved sources and signing keys. TLS for all traffic. End-to-end signatures on returned
resources when supported.

**Transport security (T7, T8, T10).** See the table in section 5.

**Secure tool and UX design (T9).**

- One clear purpose per tool, with explicit limits. Purpose-built tools over powerful ones:
  "run this prepared statement" instead of "run any SQL".
- The tool code enforces security, validation and constraints. Never leave them to the LLM.
- Do not rely on the user alone either: frequent prompts cause fatigue.
- Security prompts and elicitations state clearly what is asked and what happens.

**Human-in-the-loop (T2, T9).** Hosts usually let users switch confirmations off. Where that
is not acceptable: enforce a host/client configuration that unprivileged users cannot change,
or have the server ask for confirmation itself through elicitation.

**Logging (T12).** Log at host, client and server: which tool was chosen, with which
parameters, as a result of which prompt. An MCP gateway or proxy between clients and servers
can centralize logging. Immutable records of authorizations (for example token exchange at the
identity provider) show who asked for an action and how it was authorized. OpenTelemetry links
actions end to end.

**Lifecycle and governance (T6, T11, T12).**

- Verify code signatures before installing a server.
- Private package repositories with scanning and an approval workflow.
- Software composition analysis (SCA) for vulnerable dependencies.
- Allowlist of approved servers, each with a documented security review.
- Hash-verified packages; dependency pinning by hash, not by version range.
- Binary authorization: unsigned code does not run.
- SBOM for all MCP components; reproducible builds; secure development lifecycle for
  internal servers; watch CVE feeds.
- Central inventory of deployed servers (version, owner, purpose).
- Automatic discovery of shadow deployments.
- Lifecycle policies that retire old servers; full decommissioning.
- Configuration management; rollback; staged rollout of updates.
- Regular re-review of approved servers; forced upgrades for servers with known
  vulnerabilities.

## 5. Transport controls table

| Required control | Transport | Exploit when missing |
|---|---|---|
| Payload limits | all | large or recursive payload DoS |
| Client-server authentication and authorization | HTTP | impersonation, commands before init, unauthorized RPC calls |
| Downstream authentication and authorization | all | impersonation, unauthorized RPC calls |
| Mutual TLS | HTTP | impersonation |
| TLS encryption | HTTP | stream tampering, TLS downgrade |
| CORS policy | HTTP | cross-origin data leaks |
| CSRF protection | HTTP | forged POST requests |
| Secure descriptor handling | stdio | hijacking via inherited descriptors |
| Integrity checks | all | replay, spoofing, poisoned responses |

## 6. Deployment patterns

| Pattern | Client / server / transport | What dominates | Paper's recommendations |
|---|---|---|---|
| DP1 All-local | localhost / localhost / stdio or HTTP | Server runs with the user's rights; host posture decides everything | Fine for development and personal use. Prefer stdio (no DNS rebinding). Sandbox local servers. |
| DP2 Single-tenant remote | local or remote / one hosted server per tenant / HTTP | Auth between client and server forms the trust boundary | Tokens in OS keychain or secret manager. Authenticated and encrypted traffic. Authenticated server discovery and an allowlist (for example via MDM). |
| DP3 Multi-tenant | cloud or local / SaaS or PaaS server shared by tenants / HTTP | Tenant isolation, identity, access control | Strong multi-tenancy controls (per-tenant encryption, RBAC). Prefer the server run by the service owner itself over a third-party wrapper. Remote attestation where possible. |

Note: the paper's table of contents calls the multi-tenant pattern "Deployment Pattern 4"; the
figure calls it DP3. Both mean the same pattern.

## 7. Incidents the paper cites

- A SaaS vendor's MCP feature had a tenant isolation flaw that mixed data across up to about
  1,000 customer organizations (May 2025). Threats 10, 20.
- An AI plugin with MCP support for a widely used content management system allowed privilege escalation on over 100,000 sites,
  patched June 2025. Threat 8.
- Researchers showed that a prompt injection placed in a support ticket made a coding agent
  read private tables through an MCP server with direct database access. Threats 4, 7, 20.

## 8. Source and license

Source: CoSAI (Coalition for Secure AI, an OASIS Open Project), "Model Context Protocol (MCP)
Security", Workstream 4, version dated 8 January 2026. This file is a derivative work that
explains the paper. The notice below is required on derivative works.

> Copyright © OASIS Open 2025. All Rights Reserved. This document has been produced under the
> process and license terms stated in the OASIS Open Project rules:
> https://www.oasis-open.org/policies-guidelines/open-projects-process.
>
> This document and translations of it may be copied and furnished to others, and derivative
> works that comment on or otherwise explain it or assist in its implementation may be
> prepared, copied, published, and distributed, in whole or in part, without restriction of
> any kind, provided that the above copyright notice and this section are included on all such
> copies and derivative works. The limited permissions granted above are perpetual and will not
> be revoked by OASIS or its successors or assigns. This document and the information contained
> herein is provided on an "AS IS" basis and OASIS DISCLAIMS ALL WARRANTIES, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN
> WILL NOT INFRINGE ANY OWNERSHIP RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR
> FITNESS FOR A PARTICULAR PURPOSE. OASIS AND ITS MEMBERS WILL NOT BE LIABLE FOR ANY DIRECT,
> INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF ANY USE OF THIS DOCUMENT OR ANY
> PART THEREOF. The name "OASIS" is a trademark of OASIS, the owner and developer of this
> document, and should be used only to refer to the organization and its official outputs.
> OASIS welcomes reference to, and implementation and use of, documents, while reserving the
> right to enforce its marks against misleading uses. Please see
> https://www.oasis-open.org/policies-guidelines/trademark/ for above guidance.
>
> This is a Non-Standards Track Work Product. The patent provisions of the OASIS IPR Policy do
> not apply.
