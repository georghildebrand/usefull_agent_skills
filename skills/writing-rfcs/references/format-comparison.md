# RFC formats compared

Use this file when the repo has no format and the user wants one that
matches a known practice, or when you need to map a repo's status names.

## Section lists

| Format | Sections | When to pick |
|---|---|---|
| Rust RFC | Summary, Motivation, Guide-level explanation, Reference-level explanation, Drawbacks, Rationale and alternatives, Prior art, Unresolved questions (before merge / during implementation / out of scope), Future possibilities | Public API or language change that users must learn |
| Python PEP | Preamble headers, Abstract, Motivation, Specification, Rationale, Backwards Compatibility, Security Implications, How to Teach This, Reference Implementation, Rejected Ideas, Open Issues | Standards-like change with strong compatibility needs |
| Kubernetes KEP | Summary, Motivation (Goals, Non-Goals), Proposal (User Stories, Risks and Mitigations), Design Details (Test Plan, Graduation Criteria, Upgrade/Downgrade, Version Skew), Production Readiness questions, Drawbacks, Alternatives; metadata file | Change shipped in stages; needs rollback and production readiness |
| Go design doc | Abstract, Background, Proposal, Rationale, Compatibility, Implementation, Open issues | Lightweight; after a short issue showed a doc is needed |
| React RFC | Summary, Basic example, Motivation, Detailed design, Drawbacks, Alternatives, Adoption strategy, How we teach this, Unresolved questions | Feature with an adoption and teaching path |
| Google design doc (Ubl) | Context and scope, Goals and non-goals, The design (overview, then details), Alternatives considered, Cross-cutting concerns | Internal system design with real trade-offs |
| HashiCorp RFC | Header with owner, contributors, stakeholders, approvers; Overview, Background, Proposal, Abandoned Ideas, free-form Implementation | Product-linked change with named approvers |
| GitLab design doc | Front matter (status, authors, DRIs); Summary, Motivation, Goals, Non-Goals, Proposal, Design details, Alternative Solutions incl. "Do nothing", Decisions (links to ADRs) | Cross-team, multi-milestone work with ADR extraction |
| Oxide RFD | Metadata (authors, state, discussion link); viable options with benefits and drawbacks, reasoning, data, determination; file `rfd/NNNN/README.adoc` | Git-based team that wants discussion, not approval gates |

Common core across all of them: summary, problem, goals and non-goals,
proposal, alternatives with reasons, drawbacks, open questions. The default
templates in `templates/` use this core.

Single sections worth borrowing (Orosz, Pragmatic Engineer): "definition of
success", "why now and not later", "Risks (must have!)", "what we still do
not know", "revisit date".

## Status names

| Source | States |
|---|---|
| PEP | Draft, Accepted, Provisional, Final, Deferred, Rejected, Withdrawn, Superseded, Active |
| KEP | provisional, implementable, implemented, deferred, rejected, withdrawn, replaced |
| Oxide RFD | prediscussion, ideation, discussion, published, committed, abandoned |
| GitLab | proposed, accepted, ongoing, implemented, postponed, rejected |
| HashiCorp | WIP, In-Review, Approved, Obsolete |
| Meetup (Calcado) | Draft, Feedback Requested, Active, Abandoned, Retired |
| Default in this skill | draft, in-review, accepted, rejected, withdrawn, superseded |

The agent may set only the first state of any model (draft, WIP,
prediscussion, proposed). Every later state needs a human statement.

## Decision models

| Model | Who decides | Fields to fill |
|---|---|---|
| One owner with approvers (GitLab, Squarespace, HashiCorp) | One owner with final say; few approvers answer "yes", "not yet" or "yes, if" | Decision owner, approvers, consulted |
| Advice process (Harmel-Law) | Anyone may decide but must ask everyone affected and experts for advice, and record it. Not consensus | Decision owner, advice asked from, advice received |
| DACI (Atlassian) | One Driver, exactly one Approver, Contributors, Informed | Driver, Approver, Contributors, Informed |
| RAPID (Bain) | Recommend, Agree, Perform, Input, one Decide | Roles per letter |
| Consent (Sociocracy 3.0) | Adopted when no objection remains; an objection names a risk; a concern is recorded but does not block | Objections, concerns, review date |
| No approval gate (Oxide) | Convergence in discussion; do not merge an RFD nobody else read | Discussion link, state |

If nobody names a model, use the default in SKILL.md ("Decider model") and
tag it [Assumed: ...].

## Comment periods

React 3 calendar days. Ember 7 days. Go about one week after a "likely
accept/decline" note. Rust final comment period 10 calendar days. GitLab ADR
review about 10 days. Oxide 3-5 business days as a suggestion. Node.js at
least 48 hours for PRs. No source gives evidence for one value. Default
suggestion: 1 week, and give reviewers at least two working days (Lynch).

## Review practice

- Show the draft first to one reviewer, then to the wider group (Lynch).
- Name specific reviewers. With many recipients, each one assumes someone
  else reviews (Lynch).
- Answer questions by editing the doc. Move long threads to the open
  questions (Lynch).
- Sort comments into blocker or remark (SKILL.md, "Review rounds"). Zimmermann
  suggests a similar split: High/Medium/Low and "action needed" or "FYI".
- An accepted RFC is not approval to start work or a priority (Rust; Calcado).
