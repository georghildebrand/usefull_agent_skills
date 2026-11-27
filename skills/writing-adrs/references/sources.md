# Sources

The sources this skill is based on. Each line: author, title, year (when
known), URL, and what the skill takes from it.

## ADR definition, formats and templates

- Michael Nygard, "Documenting Architecture Decisions", 2011.
  https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions
  Sections, "We will ...", list all consequences, 1 to 2 pages, numbers never reused.
- adr organisation, MADR 4.0.0 template, 2024.
  https://github.com/adr/madr/blob/4.0.0/template/adr-template.md
  Front matter, considered options, confirmation, variants.
- adr organisation, "About MADR", 2024. https://adr.github.io/madr/
- adr.github.io, home page and ADR templates. https://adr.github.io/ and https://adr.github.io/adr-templates/
  Definitions of decision, significant requirement and decision log.
- Olaf Zimmermann, "MADR Template Primer", 2022.
  https://www.ozimmer.ch/practices/2022/11/22/MADRTemplatePrimer.html
  Real options at the same level, operator and maintainer view.
- Olaf Zimmermann, "Architectural Decisions - The Making Of", 2020.
  https://www.ozimmer.ch/practices/2020/04/27/ArchitectureDecisionMaking.html
  Y-statement.
- Olaf Zimmermann, "A Definition of Done for Architectural Decision Making", 2020.
  https://ozimmer.ch/practices/2020/05/22/ADDefinitionOfDone.html
  "Sometimes, there only is one choice (which should still be justified)".
- Olaf Zimmermann, "ADR = Any Decision Record?", 2021.
  https://ozimmer.ch/practices/2021/04/23/AnyDecisionRecords.html
- Olaf Zimmermann, "How to create Architectural Decision Records (ADRs) - and how not to", 2023.
  https://ozimmer.ch/practices/2023/04/03/ADRCreation.html
  Writing anti-patterns.
- Olaf Zimmermann, "How to review Architectural Decision Records (ADRs) - and how not to", 2023.
  https://ozimmer.ch/practices/2023/04/05/ADRReview.html
  Review questions and review anti-patterns.
- Olaf Zimmermann, "A Definition of Ready for Architectural Decisions", 2023.
  https://ozimmer.ch/practices/2023/12/01/ADDefinitionOfReady.html
- Jeff Tyree and Art Akerman, decision record template, 2005 (rendering by Joel Parker Henderson).
  https://github.com/joelparkerhenderson/architecture-decision-record/tree/main/locales/en-001/templates/decision-record-template-by-jeff-tyree-and-art-akerman
- ISO/IEC/IEEE, FDIS 42010, 2011.
  http://www.iso-architecture.org/ieee-1471/docs/_PRIVATE/ISO-IEC-FDIS-42010.pdf
  Criteria for key decisions.
- arc42, "Section 9: Architecture Decisions". https://docs.arc42.org/section-9/
- Andrew Harmel-Law, "Scaling the Practice of Architecture, Conversationally".
  https://martinfowler.com/articles/scaling-architecture-conversationally.html
  Advice process and Advice section.
- UK Government, "Architectural Decision Record Framework", 2025.
  https://www.gov.uk/government/publications/architectural-decision-record-framework/architectural-decision-record-framework

## Process, storage and tools

- Joel Parker Henderson, architecture-decision-record (README and skill), 2026.
  https://github.com/joelparkerhenderson/architecture-decision-record
  Detect the existing folder first; supersede links both ways.
- Nat Pryce, adr-tools. https://github.com/npryce/adr-tools
  Default status "Accepted", spelling "Superceded", `-s` and `-l` options.
- Thomas Vaillant, log4brains. https://github.com/thomvaill/log4brains
  Date-prefixed file names.
- Backstage, "Architecture Decision Records". https://backstage.io/docs/architecture-decisions/
  Number set before merge, `backstage.io/adr-location` annotation.
- AWS, "Prescriptive Guidance: ADR process".
  https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html
  Owner proposes; review decides; rejected ADRs keep the reason.
- Microsoft, "Maintain an architecture decision record", Azure Well-Architected Framework, 2026.
  https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
- Google Cloud, "Architecture decision records overview".
  https://docs.cloud.google.com/architecture/architecture-decision-records
- UK Government Digital Service, "GDS Way: Documenting architecture decisions".
  https://gds-way.digital.cabinet-office.gov.uk/standards/architecture-decisions.html
  Pull request state as status.
- Thoughtworks, "Lightweight Architecture Decision Records", Technology Radar, 2016-2018.
  https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records
- Martin Fowler, "Architecture Decision Record", 2026.
  https://martinfowler.com/bliki/ArchitectureDecisionRecord.html
- Red Hat, "Why you should be using architecture decision records to document your project".
  https://www.redhat.com/en/blog/architecture-decision-records

## When to write an ADR, and ADR versus RFC

- Josef Blake, "When Should I Write an Architecture Decision Record", Spotify Engineering, 2020.
  https://engineering.atspotify.com/2020/04/when-should-i-write-an-architecture-decision-record
- Pierre Pureur and Kurt Bittner, "Has Your Architectural Decision Record Lost Its Purpose?", InfoQ, 2023.
  https://www.infoq.com/articles/architectural-decision-record-purpose
- designdoc.tech, "RFCs vs ADRs: When to Use Which". https://designdoc.tech/blog/rfcs-vs-adrs
- Plannotator, "ADR vs RFC vs Technical Specification".
  https://docs.plannotator.ai/compare/adr-vs-rfc-vs-technical-specification
- GitLab, "Architecture Design Workflow". https://handbook.gitlab.com/handbook/engineering/architecture/workflow/
- Thoughtworks, "Lightweight approach to RFCs", Technology Radar, 2023.
  https://www.thoughtworks.com/radar/techniques/lightweight-approach-to-rfcs

## Studies on ADRs and on ADRs written by language models

- Buchgeher et al., "Using Architecture Decision Records in Open Source Projects - An MSR Study on GitHub", IEEE Access, 2023.
  https://research.jku.at/en/publications/using-architecture-decision-records-in-open-source-projects-an-ms/
- "Architecture Decision Records Adoption, Impact and Developer Engagement in Open Source", ICSA 2026.
  https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou
  About 63% of ADRs created directly as accepted.
- Dhar et al., "Can LLMs Generate Architectural Design Decisions? An Exploratory Empirical Study", 2024.
  https://arxiv.org/html/2403.01709v1
- Dhar et al., "DRAFT-ing Architectural Design Decisions using LLMs", 2025. https://arxiv.org/abs/2504.08207
- "Context Matters: Evaluating Context Strategies for Automated ADR Generation Using LLMs", 2026.
  https://arxiv.org/html/2604.03826v1
  The 3 to 5 most recent ADRs are enough context; output about twice as long without context.
- Zhou et al., "Using LLMs in Generating Design Rationale for Software Architecture Decisions", TOSEM, 2025.
  https://arxiv.org/html/2504.20781
  Too many arguments, bias towards advantages.
- "AgenticAKM: Enroute to Agentic Architecture Knowledge Management", 2026.
  https://arxiv.org/html/2602.04445v1
  Separate checking agents improve quality.
- "GADR: Gathering Architecture Decision Records from Meeting Transcriptions", 2026.
  https://arxiv.org/abs/2608.17694

## Other agent skills compared

- Anthropic, doc-coauthoring skill.
  https://raw.githubusercontent.com/anthropics/skills/main/skills/doc-coauthoring/SKILL.md
  Reader test by a fresh subagent.
- GitHub, awesome-copilot create-architectural-decision-record skill.
  https://raw.githubusercontent.com/github/awesome-copilot/main/skills/create-architectural-decision-record/SKILL.md
- affaan-m, ECC architecture-decision-records skill.
  https://raw.githubusercontent.com/affaan-m/ECC/main/skills/architecture-decision-records/SKILL.md
  Draft first, write after approval; length limits per section.
- Donchitos, Claude-Code-Game-Studios architecture-decision skill.
  https://raw.githubusercontent.com/Donchitos/Claude-Code-Game-Studios/main/.claude/skills/architecture-decision/SKILL.md
  New ADRs always proposed; review in a separate session.
- milenkotomic, design-doc. https://github.com/milenkotomic/design-doc
  Decided / Assumed / Open tags; claims checked against code.
