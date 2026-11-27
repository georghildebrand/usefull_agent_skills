# ADR formats, status words, paths and numbering

Read this in step 1 of the skill, when you detect the repository's
conventions. Follow what the repository already does. Use the defaults here
only when it does nothing.

## Formats compared

| Format | Sections | Pick it when |
|---|---|---|
| Nygard (2011) | Title, Status, Context, Decision, Consequences | Default. The most used format in public repositories. |
| adr-tools default | `# NUMBER. TITLE`, Date, Status, Context, Decision, Consequences | The repository already uses adr-tools. |
| MADR 4.0.0 (2024) | Optional YAML front matter (status, date, decision-makers, consulted, informed). Required: title, Context and Problem Statement, Considered Options, Decision Outcome. Optional: Decision Drivers, Consequences, Confirmation, Pros and Cons of the Options, More Information. Variants: full, minimal, bare, bare-minimal. | Real alternatives exist and should be compared. |
| Y-statement (Zimmermann) | One sentence: in the context of ..., facing ..., we decided for ... and against ..., to achieve ..., accepting that ... | Summary line at the top of an ADR or in a PR description. Also a completeness check. |
| Harmel-Law (advice process) | Title, Status, Decision, Context, Options considered, Consequences, Advice (name and date of each advisor) | The team uses the advice process. Fill Advice only with advice the user reports. |
| GOV.UK framework (2025) | Title, date, status, context, decision, consequences, stakeholders consulted, links | Public sector, or decisions that need a named approval level. |
| Tyree and Akerman (2005) | 14 fields, from Issue to Notes | Formal settings only. Too heavy for most repositories. |
| ISO/IEC/IEEE 42010 decision record | Identifier, statement, concerns, owner, affected elements, rationale, constraints, effect on other decisions, timestamps | The team must follow the standard. |
| arc42 section 9 | Points to Nygard format; key decisions also in section 4 | The repository already uses arc42. |

## Status words

Sources use different words. A common set: proposed, accepted, rejected,
deprecated, superseded by NNNN.

- Nygard: proposed, accepted, deprecated, superseded. No "rejected".
- MADR: proposed, rejected, accepted, deprecated, "superseded by ADR-NNNN".
- adr-tools: a new ADR gets "Accepted" by default. Its link text is spelled
  "Superceded by" and "Supercedes" (with a c). Keep the tool's spelling in a
  repository that uses it, but change the default status to proposed.
- GDS Way: in GitHub the pull request state is the status. An ADR merged to
  main counts as accepted.

The agent writes only "proposed". It means the same as `draft` in an RFC:
not yet decided by a human. In a repository where the pull request is
the status, the agent opens a draft pull request and does not set a status
word that says accepted.

Keep rejected ADRs. Record the reason, so the same discussion does not start
again.

## Paths and file names

| Source | Path |
|---|---|
| Nygard | `doc/arch/adr-NNN.md` |
| adr-tools | `doc/adr/NNNN-slug.md` (or `doc/architecture/decisions`) |
| MADR | `docs/decisions/NNNN-title-with-dashes.md` |
| log4brains | `docs/adr/YYYYMMDD-slug.md`, also per package in a monorepo |
| Backstage plugin | Path from the annotation `backstage.io/adr-location` |

Default when nothing exists: `docs/decisions/NNNN-<decision-as-short-phrase>.md`.
Ask before you create a new ADR folder.

Where the file belongs: an ADR for one application goes in that application's
repository. A decision for many repositories goes in a central repository that
the others link to.

## Numbering

- Sequential numbers never repeat, also not for rejected or superseded ADRs.
- adr-tools pads the file name to 4 digits (`0008-...`) but not the heading
  (`# 8. ...`).
- Next number = highest number on the target branch + 1. Check the target
  branch, not only the current one.
- Parallel branches can pick the same number. Warn the user. Two other schemes
  avoid this: a date prefix (log4brains) or a placeholder number that is set
  just before merge (Backstage drafts use `adr000-<name>.md`).

## Supersede and amend

- New ADR: "Supersedes NNNN" (or "Amends NNNN"), as a link.
- Old ADR: only the status line changes, to "Superseded by NNNN" (or "Amended
  by NNNN"), as a link. The body stays as it is. Never delete an old ADR.
- adr-tools does both with `adr new -s 9 "Title"`, or `-l "5:Amends:Amended by"`.
  It also writes the status "Accepted", which you change to proposed.

**Edit or replace?** Sources disagree. Many (AWS, Azure, Fowler, log4brains)
say accepted ADRs never change; a change needs a new ADR. Some teams add dated
notes to an existing ADR instead. GDS allows edits to an ADR that was never
implemented, if reviewers agree. Default: keep the body, change only the
status line. Add a dated "Note added after decision" only if the repository
already does this.

## Significance threshold

Sources disagree on how often to write an ADR:

- Low threshold (Spotify): "almost always", even for small decisions, so
  small differences do not grow into competing solutions.
- High threshold (Pureur and Bittner): only when the decision is both costly
  to undo and shapes the basic approach.
- In between: Nygard and AWS list structure, quality attributes, dependencies,
  interfaces and construction methods. ISO 42010 lists decisions that are
  costly to change, affect many people, or have reasons that are not obvious.
  Zimmermann: "if in doubt, leave it out".

If the repository or team guide states a threshold, use it. If not, use the
significance points in the routing table of SKILL.md and say which threshold
you applied.
