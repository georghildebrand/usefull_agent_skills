<!--
Default full RFC template (writing-rfcs skill).
Use it only when the repo and loaded skills define no format of their own.
For an open decision that is hard to undo or affects more than one team.

Rules while filling it:
- Every slot marked REQUIRED stays, also when the answer is a placeholder.
- Leave out an optional section that has no real content. Delete its heading.
- Mark challengeable statements [Decided], [Assumed: ...] or [Open: ...].
- Names only from the user; otherwise the placeholders below.
- Delete all these comments before you show the draft.
- Aim for 3-10 pages. Above ~10 pages, suggest a split into several RFCs.
-->

# RFC NNNN: <short title that names the change>

| Field | Value |
|---|---|
| Status | draft <!-- REQUIRED. Never set accepted/approved yourself. --> |
| Created | <YYYY-MM-DD> |
| Author(s) | <names the user gave, or AUTHOR: to be named> |
| Decision owner | <OWNER: to be named> <!-- REQUIRED. One person with the final say. --> |
| Approvers / advisers | <APPROVER: to be named> <!-- REQUIRED. Few people. CODEOWNERS teams may be listed as "suggested". --> |
| Consulted (advisory, does not block) | <teams or roles affected> |
| Decision model | <one owner with few approvers (default) / another model the team names> |
| Review deadline | <DEADLINE: to be set, suggest 1 week> <!-- REQUIRED. --> |
| Discussion link | <PR, issue or thread URL, or [Open: where?]> |
| Supersedes / related | <existing RFCs or ADRs, written exactly as the repo names them> |

**Feedback needed:** <REQUIRED. One line. Example: "Approvers: is the event
contract in section 5 acceptable? Everyone: are there consumers we missed?">

## 1. Summary

<One paragraph. Readable alone: many readers stop here. What changes, for
whom, and the main trade-off.>

## 2. Background

<What a new engineer needs to know to follow the rest. At most one page.
Every fact about the current system cites a file path, a user statement or a
linked document.>

## 3. Problem

<The concrete problem, with evidence and its source. Why now, and not later.
If the problem is not concrete yet, say so: the RFC is not ready.>

## 4. Goals and non-goals

**Goals** <!-- REQUIRED -->
- <outcome a reviewer can check>

**Non-goals** <!-- REQUIRED. Things a reader could expect, but that are out of scope. -->
- <example: "Changing the invoice data model">

## 5. Proposal

<Overview first, then details. Focus on trade-offs. No pasted full schemas
or full interfaces: link to them. Code only for a new algorithm.>

## 6. Cross-cutting concerns

<Security, privacy, observability and monitoring, rollout, rollback,
migration, cost. Leave out a line only if it really does not apply, and say
why in a few words.>

## 7. Alternatives

### 7.1 Do nothing <!-- REQUIRED. Keep the label "Do nothing". -->

- What happens if we change nothing: <cost, risk, or "acceptable for now">
- Why not chosen: <reason>

### 7.2 <Alternative name>

- How it would solve the problem: <one or two sentences>
- Upsides: <...>
- Downsides: <at least one>
- Why not chosen: <reason>

<If only one option is viable, write that here and explain why. Do not add
a weak option to fill the list.>

## 8. Drawbacks

<REQUIRED, never empty. Answer: "Why should we not do this?">

## 9. Prior art (optional)

<What others did, good and bad. Precedent alone is not a reason to accept.>

## 10. Open questions

**Before acceptance**
- [Open: <question>]

**During implementation**
- [Open: <question>]

**Out of scope for this RFC**
- <question>

## 11. Change log

<Optional. Added in review rounds: date, comment, blocker or remark, action
(accepted, declined with reason, escalated).>

## 12. Decision

<Left empty until a human states the outcome. Then: outcome, who decided,
date, reasons. Also filled for rejected or withdrawn RFCs. ADRs written from
this RFC link to this section.>

## 13. ADRs to write

<REQUIRED. Last section. One line per open decision in this RFC. After
acceptance, each line becomes one ADR (writing-adrs) with status proposed.>

- [ ] ADR: <decision, for example "Use an outbox table for order events">
- [ ] ADR: <decision>
