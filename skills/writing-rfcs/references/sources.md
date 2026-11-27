# Sources

Sources this skill is based on. Year is given where the source states one.

## RFC processes and templates

- RFC template (0000-template.md) and README - Rust project - current - https://github.com/rust-lang/rfcs
- Proposals and stabilization (compiler) - Rust Forge - current - https://forge.rust-lang.org/compiler/proposals-and-stabilization.html
- PEP 1: PEP Purpose and Guidelines - Python - current - https://peps.python.org/pep-0001/
- KEP template and KEP-0000 process - Kubernetes - current - https://github.com/kubernetes/enhancements
- Production Readiness Review - Kubernetes - current - https://github.com/kubernetes/community/blob/master/sig-architecture/production-readiness.md
- RFC template and README - React - current - https://github.com/reactjs/rfcs
- RFC README - Ember - current - https://github.com/emberjs/rfcs
- Proposal README and design/TEMPLATE.md - Go - current - https://github.com/golang/proposal
- Collaborator Guide - Node.js - current - https://github.com/nodejs/node/blob/main/doc/contributing/collaborator-guide.md
- RFD 1 Requests for Discussion - Oxide Computer - current - https://rfd.shared.oxide.computer/rfd/0001
- RFC template - HashiCorp - current - https://www.hashicorp.com/en/how-hashicorp-works/articles/rfc-template
- Design document template and Architecture Design Workflow - GitLab - current - https://handbook.gitlab.com/handbook/engineering/architecture/workflow/

## Practice and critique

- Design Docs at Google - Malte Ubl - 2020 - https://www.industrialempathy.com/posts/design-docs-at-google/
- Scaling Engineering Teams via RFCs: Writing Things Down - Gergely Orosz - https://blog.pragmaticengineer.com/scaling-engineering-teams-via-writing-things-down-rfcs/
- Software Engineering RFC and Design Doc Examples - The Pragmatic Engineer - https://blog.pragmaticengineer.com/rfcs-and-design-docs/
- The Power of "Yes, if" - Squarespace Engineering - 2019 - https://engineering.squarespace.com/blog/2019/the-power-of-yes-if
- RFCs and review councils - Brandur Leach - https://brandur.org/fragments/rfcs-and-review-councils
- A Structured RFC Process - Phil Calcado - 2018 - https://philcalcado.com/2018/11/19/a_structured_rfc_process.html
- RFC process for teams - Attentive - https://tech.attentive.com/articles/rfc-process-for-teams
- Never approve design docs - Jos Visser - https://josvisser.substack.com/p/never-approve-design-docs
- Design docs considered harmful - Lucas F. Costa - https://www.lucasfcosta.com/blog/design-docs
- How to Get Meaningful Feedback on Your Design Document - Michael Lynch - https://refactoringenglish.com/blog/useful-feedback-on-design-docs/
- Planning for change with RFCs - Vaidehi Joshi, Increment - 2021 - https://increment.com/planning/planning-with-requests-for-comments/
- Lightweight approach to RFCs - Thoughtworks Technology Radar - 2023 - https://www.thoughtworks.com/radar/techniques/lightweight-approach-to-rfcs

## RFC and ADR boundary

- When Should I Write an Architecture Decision Record - Josef Blake, Spotify - 2020 - https://engineering.atspotify.com/2020/04/when-should-i-write-an-architecture-decision-record
- RFCs vs ADRs: When to Use Which - designdoc.tech - https://designdoc.tech/blog/rfcs-vs-adrs
- ADR vs RFC vs Technical Specification - Plannotator - https://docs.plannotator.ai/compare/adr-vs-rfc-vs-technical-specification
- Scaling the Practice of Architecture, Conversationally - Andrew Harmel-Law - https://martinfowler.com/articles/scaling-architecture-conversationally.html

## Decision models

- DACI decision-making framework - Atlassian Team Playbook - https://www.atlassian.com/team-playbook/plays/daci
- RAPID decision making - Bain - https://www.bain.com/insights/rapid-decision-making/
- Consent Decision-Making - Sociocracy 3.0 - https://patterns.sociocracy30.org/consent-decision-making.html

## Anti-patterns and review

- How to create ADRs - and how not to - Olaf Zimmermann - 2023 - https://ozimmer.ch/practices/2023/04/03/ADRCreation.html
- How to review ADRs - and how not to - Olaf Zimmermann - 2023 - https://ozimmer.ch/practices/2023/04/05/ADRReview.html

## Agents and LLMs

- Using LLMs in Generating Design Rationale for Software Architecture Decisions - Zhou et al., TOSEM - 2025 - https://arxiv.org/html/2504.20781
- LLVM RFC seeks ban on AI text in PRs and proposals - freenode.net (news report on a draft RFC) - 2026 - https://freenode.net/article/llvm-rfc-seeks-ban-on-ai-text-in-prs-and-proposals
- doc-coauthoring SKILL.md - Anthropic - https://github.com/anthropics/skills
- design-doc README - milenkotomic - https://github.com/milenkotomic/design-doc
- rfc SKILL.md - paritytech/trinity-user-agents - https://github.com/paritytech/trinity-user-agents

## Ideas taken from the agent skills above

- Reader test with a fresh subagent that sees only the doc (doc-coauthoring).
- Decided / Assumed / Open tags, checking user claims against code, and the
  accept / decline / escalate review rounds (design-doc).
- `status: draft` by default, omit sections filled only for the template,
  prefer a stated assumption over a blocking question (paritytech rfc).
- Gap filled by this skill: none of the three ends with a list of ADRs to
  write, and none makes the decision owner and review deadline required.
