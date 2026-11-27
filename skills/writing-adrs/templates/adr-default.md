<!--
Default ADR template of the writing-adrs skill.
Use it only when the repository, a loaded skill or a team guide gives no format.
Based on the Nygard sections (Status, Context, Decision, Consequences) plus
MADR 4 fields (drivers, options, confirmation).
Suggested path: docs/decisions/NNNN-<decision-as-short-phrase>.md

Rules while filling:
- Write a sentence only if it has a source (user, code, earlier ADR, linked doc).
- Tag everything else as [Assumed: ...] or [Open: question].
- Names only from the user; otherwise the placeholders below.
- Delete an optional section rather than fill it with guesses.
- Do not add list items to reach a number. One real item is fine.
- Delete this comment before handover.
-->

# NNNN. <Decision as a short phrase, e.g. "Use PostgreSQL for the orders service">

- Status: proposed
- Date: <YYYY-MM-DD the draft was written>
- Decision owner: <OWNER: to be named>
- Approvers: <APPROVER: to be named>
- Consulted (advisory, does not block): <teams or roles, or delete this line>
- Supersedes / Amends: <link to earlier ADR, or delete this line>
- Related RFC: <link to the RFC's Decision section, or delete this line>

## Context

<2 to 5 sentences of neutral facts: what exists today, what problem appears,
why a decision is needed now. Link supporting documents. The ADR must still
make sense without them.>

## Decision drivers

<The needs that decide between the options, most important first.
Optional section. Delete it if no driver has a source.>

- <driver>

## Considered options

<Real options only, at the same level. Chosen option first.
If there is only one: "Only one option was considered because ...".>

1. <chosen option>
2. <other option>

## Decision

We will <the decision in 1 to 3 sentences, active voice>.

<One sentence on the main reason, linked to the drivers above.>

## Consequences

<At least one negative consequence and one effect on operations or
maintenance. Tag them [Open: ...] if no source names them yet.>

- Good: <...>
- Bad: <...>
- Operations and maintenance: <backups, upgrades, monitoring, migrations, on-call ...>

## Options in detail

<Optional. For each option that was not chosen: why not, in one or two lines.>

### <other option>

- Good: <...>
- Bad: <...>
- Why not chosen: <...>

## Confirmation

<Optional. How the team will check that the code follows the decision:
a review rule, a test, a lint rule.>

## Review trigger

<Optional. When to look at this decision again: a date, or an event such as
"if write volume grows more than 10x" (only with a sourced number).>

## Change log

<Optional. Added in review rounds: date, comment, action (accepted,
declined with reason, escalated).>
