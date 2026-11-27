---
name: writing-adrs
description: >
  Use when an option is already chosen or nearly chosen and the reason must be
  recorded: write, draft, update or supersede an Architecture Decision Record
  (ADR), decision record or decision log entry; record a choice of database,
  protocol, framework or service boundary; turn the "ADRs to write" list of an
  accepted RFC into ADRs; or document an old decision found in the code. Not
  for a choice that is still open and needs comments before anyone decides
  (use writing-rfcs), not for small easy-to-undo changes such as version
  bumps, renames or bug fixes (PR description), not for how-to guides or
  READMEs, and not for only reviewing someone else's ADR.
---

# Writing ADRs

## Overview

An Architecture Decision Record (ADR) is a short file in the repository. It
records one architecture decision: the situation, the options, the choice and
its effects. A later reader uses it to see why the system looks the way it does.

An agent that writes an ADR fails in known ways. It invents reasons that only
people know. It lists too many arguments, mostly positive ones. It adds a weak
option so the choice looks compared. It sets the status to "Accepted" on its
own. A template does not stop any of this. This skill uses two rules instead:

1. **Every statement a reader could question has a source.** The source is the
   user, the code, an earlier ADR, an RFC, a linked document, or nothing. A
   statement with no source is tagged in the draft as assumed or open.
2. **The agent proposes, a human decides.** The agent prepares a change to the
   decision log (the folder of all ADRs) with status "proposed". A human or a
   merge accepts it.

## When to use, and what to write instead

Route first. This table is the same in the `writing-rfcs` skill.

| Situation | Write | Skill |
|---|---|---|
| A choice is still open and people must comment before a human decides. It is hard to undo (public API, database schema, service boundary, data ownership) or affects more than one team. | Full RFC | writing-rfcs |
| A choice is still open and needs input, but it is easy to undo and stays inside one team. | Short RFC (1 to 3 pages) | writing-rfcs |
| An option is chosen or nearly chosen (by the user, a meeting or merged code), and the decision is significant: hard to undo, changes the structure, an interface or a key quality, adds a dependency that is hard to replace, affects several teams, or has reasons the code does not show. | One ADR per decision | writing-adrs |
| An accepted RFC lists settled decisions under "ADRs to write". | One ADR per line, each linking the RFC's Decision section | writing-adrs |
| A small change with no real alternative that is easy to undo: version bump, rename, refactor, bug fix, flaky test fix. | PR description or commit message | none |
| How to build or run something: steps, settings, code structure, with no open choice. | Guide or README | none |
| The decision is already recorded and nothing changed. | Nothing. Link the existing ADR. | none |
| Nothing is chosen or proposed yet. The user is still exploring and cannot name the problem. | No document yet. Ask what problem they want solved. | none |

If none of the significance points in the ADR row is true, route to the PR
description. If the user still wants an ADR, write a short one
(`templates/adr-short.md`). Sources set the threshold differently; see
`references/formats.md`.

**Reply when you route away from an ADR.** Keep it under about 120 words, in
this order: one sentence on why this is not an ADR; where to record it instead;
an optional paste-ready text of at most 6 lines; one sentence on what would
change your answer. Nothing else: no repository report, no list of questions.

## Rules shared with writing-rfcs

These rules have the same wording in both skills.

**Format.** If another loaded skill or a repository document (template, team
guide, existing records) defines an ADR or RFC format, follow it. This skill
gives only the default. If a loaded skill and the repository disagree, follow
the repository and tell the user about the conflict.

**Status.** `draft` (RFC) and `proposed` (ADR) both mean: not yet decided by a
human. The agent never sets any later status. Only a human, or the merge of a
pull request where the team's process treats the merge as the decision, moves
a document past that state.

**Decider model (default).** One decision owner has the final say. A few named
approvers must agree. Everyone else is consulted; their advice does not block.
The team can configure another model (for example an advice process or
consent); use it when the user, the repository or a loaded skill names one.
Write names only when the user gave them. Otherwise write the placeholders
`<OWNER: to be named>` and `<APPROVER: to be named>`.

**Missing context.** Ask at most 3 questions per round. Ask only questions
whose answer changes the chosen option or the scope. Fill every other gap with
a tag (below) and go on. If the user cannot answer now, draft with tags.
For an ADR: stop and reply "not ready", with what is missing, when you cannot
name the problem, or cannot name two real options (the chosen one and one
alternative, or a sourced reason why only one option exists).

**Tags for uncertain statements.** `[Assumed: ...]` means you filled it in; it
is likely but not confirmed. `[Open: question]` means nobody has said it and a
human must answer. A statement with no source carries one of these tags and is
never written as fact. If the repository already uses another marker, such as
`[TODO: ...]`, use that one.

**Review rounds.** When reviewers comment on a draft, sort each comment into
**blocker** (must be resolved before a human decides) or **remark** (does not
block). For each comment: accept it and change the text, decline it with a
reason, or escalate it to the decision owner. Record each one in a short
"Change log" section of the document: date, comment, action. Keep the tags
up to date. A review round never changes the status.

## Steps

### 1. Read the decision log before you write

- Find the folder: `git ls-files | grep -iE '(^|/)(adr|adrs|decisions?)(/|$)'`.
  Common places: `doc/adr`, `docs/adr`, `docs/decisions`, `doc/architecture/decisions`.
- Find the format (see **Format** above): the repository's template or team
  guide; a loaded skill that defines one; the 3 to 5 most recent ADRs. Use
  this skill's templates only when none of these exists.
- Note: numbering (sequential `NNNN-slug.md`, date prefix, or number given at
  merge), where the status lives (YAML front matter or a `## Status` section),
  tools (adr-tools, log4brains, a Backstage `backstage.io/adr-location`
  annotation), and any index or README that lists the ADRs.
- Read the code the decision touches. Read ADRs that the new one changes or
  depends on.

Details on formats, tools and numbering: `references/formats.md`.

### 2. Collect the claims and their sources

List every statement a reader could question: facts about today's system, the
problem, the drivers (the needs that decide between options), each option, each
reason, each consequence, people and dates. Give each one source:

| Source | Meaning |
|---|---|
| `user` | The user said it in this conversation. |
| `code:<path>` | The code or config shows it. |
| `adr:<NNNN>` | An earlier ADR states it. |
| `rfc:<path>#<section>` | An RFC states it, usually its Decision section. |
| `doc:<link>` | A document the user named or linked. |
| `assumed` | No source. Tagged `[Assumed: ...]` in the draft. |
| `open` | No source and no good guess. Tagged `[Open: question]` in the draft. |

Check user statements about the current system against the code. If they
conflict ("we use PostgreSQL" but the code uses MySQL), show the conflict.
Do not write either version as fact.

This list is the claim list. It goes into your reply, not into the ADR.

**Backfill** (writing an ADR for a decision made long ago): the sources are
code and commits, rarely `user`. Write "Reconstructed from code on YYYY-MM-DD"
(today's date) in the ADR. Use the original decision date only if a commit or
document shows it.

### 3. Input from an RFC

When the input is an RFC:

- If the RFC is still `draft`, no decision exists yet. Do not write ADRs.
  Say so, and point to writing-rfcs.
- If a human has stated the outcome in the RFC's Decision section, write one
  ADR per line of its "ADRs to write" list. Do not merge several lines into
  one ADR.
- Take context, options and reasons from the RFC, with source
  `rfc:<path>#<section>`. Do not add options or reasons the RFC does not have.
- Link back: set "Related RFC" to the RFC's Decision section. If the RFC has a
  place for links to its ADRs, list that link change in step 5.
- The ADR still starts as "proposed". An accepted RFC does not make the ADR
  accepted. A human, or the merge of the pull request, does that.

### 4. Ask, then draft

Follow **Missing context** above. The questions that most often change an ADR
are: why this option, why not the main alternative, and what it costs. Do not
ask the user to choose the status. It is always "proposed".

Use the format from step 1. Without one, use `templates/adr-default.md`, or
`templates/adr-short.md` for a small decision.

- Title: the decision as a short phrase. "Use PostgreSQL for the orders
  service", not "Database".
- Context: 2 to 5 sentences of neutral facts. Decision: 1 to 3 sentences, "We
  will ...". About one page in total, two at most.
- Options: list only real options from the sources, at the same level (product
  against product, not product against approach). If there is only one, write
  "Only one option was considered because ..." or tag that reason `[Open: ...]`.
- Consequences: at least one negative consequence and one effect on operations
  or maintenance (backups, upgrades, on-call, migrations). If no source names
  one, write a tag. Do not invent a downside to fill the slot.
- Write a sentence only if its claim has a source or a tag.
- People: follow **Decider model** above. Names only from the user; otherwise
  placeholders.

### 5. Plan the whole change, not only the new file

The output is a set of file changes:

- **New ADR.** Path and number from step 1. Next number = highest number on the
  target branch + 1, padded as the repository pads. Never reuse a number.
  Warn when other open branches may add ADRs with the same number.
- **Superseded ADR.** When the new ADR replaces an old one, write "Supersedes
  NNNN" in the new one. In the old one change only the status line to
  "Superseded by NNNN". Never change its body. Say whether this edit lands
  now or when the new ADR is accepted, following the repository's habit.
- **Amended ADR.** Same, with "Amends" and "Amended by".
- **Index.** Add a line to the ADR index or README, if one exists.
- **RFC link.** If the decision came from an RFC, link the RFC's Decision
  section from the ADR, and tick or link the matching line in the RFC's
  "ADRs to write" list if the repository does that.

### 6. Check, review, then hand over

1. Run the self-check list below. Fix what fails.
2. Start a fresh subagent as reviewer with `references/reviewer-prompt.md`. It
   gets only the draft and the claim list, not this conversation. Fix its
   blockers, or list them as open items.
3. Show the user, in this order: the draft; the list of file changes; the open
   items (every `[Assumed]` and `[Open]` tag and who should close it); at
   most 3 questions; then ask "Shall I write these files?"
4. Write files only after the user says yes. If you cannot write in this
   session, say so and give the paths. Never say a file exists when it does not.

For later comments from human reviewers, use **Review rounds** above.

## Hard rules

1. **Status is always "proposed".** Never write accepted, approved, rejected
   or deprecated. This holds when the user says the team already decided, when
   the ADR comes from an accepted RFC, and when the tool's default is
   "Accepted" (adr-tools). Tell the user how a human changes it: by review, or
   by merging the pull request.
2. **Never invent** people, roles, dates, numbers, costs, benchmarks, advice,
   meetings, agreement or reasons. Use a tag or a placeholder instead.
3. **Format:** see **Format** above.
4. **Never edit the body of an accepted ADR.** Only its status line changes.
5. **Show the draft first. Write files only after an explicit yes.**
6. **Tag what is not sourced.** Every assumed or open statement is visible in
   the draft.
7. **One decision per ADR.** Split a phased plan or a bundle of choices.

| What you think | What is true |
|---|---|
| "The user said the team already decided, so the status is Accepted." | The user told you the decision, not that it passed review. Write proposed. Say: "Change it to accepted when you merge, if your process allows that." |
| "The RFC was accepted, so its ADRs are accepted too." | The RFC decision is the input. Each ADR is a new text that a human must still review. Write proposed. |
| "adr-tools writes Accepted by default, so I keep it." | The default is the tool's, not the team's choice. Change it to proposed and say why. |
| "An empty Consequences section looks unfinished." | A tag is honest. An invented downside is a false record. |
| "Two options look better than one." | A weak option added for show is a known anti-pattern. One sourced option plus a reason is correct. |
| "I'll ask everything so the ADR is complete." | Long question lists get no answers. Ask 3, tag the rest. |

## Self-check before handover

- [ ] Routing was done. An open question went to writing-rfcs, a small change to the PR description.
- [ ] Location, number, file name and format match the repository (or the loaded skill).
- [ ] Status is proposed.
- [ ] Every sentence maps to a line in the claim list. Assumed and open claims carry visible tags.
- [ ] No invented people, numbers, dates, advice or agreement. Missing names are placeholders.
- [ ] Claims about the current system were checked against the code. Conflicts are shown.
- [ ] Options are real and at the same level. A single option has a reason or a tag.
- [ ] At least one negative consequence and one operations or maintenance effect, sourced or tagged.
- [ ] No sales words ("seamless", "best", "robust") and no scores without a source.
- [ ] One decision. About one page. Context 2 to 5 sentences, Decision 1 to 3.
- [ ] Superseded or amended ADRs change only in the status line.
- [ ] An ADR from an RFC links the RFC's Decision section.
- [ ] Not more than 3 questions to the user.
- [ ] The file-change list and the open-items list are in the reply.
- [ ] No file was written without a yes.

## Common mistakes

| Mistake | Seen as | Fix |
|---|---|---|
| Status set to Accepted because the user said "we decided" | A filled draft with "## Status Accepted" | Hard rule 1. Proposed, plus one sentence on how a human accepts it. |
| Six or more questions in one reply | Questions on format, hosting, owner and status next to the real ones | Keep the 3 that change the option or the scope. Tag the rest. |
| A long reply when no ADR is needed | Repository findings, open questions and extra sections for a version bump | Use the short routing reply: why, where instead, optional snippet, what would change the answer. |
| Draft shown but no question about writing | "Here is the draft." and the turn ends | End with "Shall I write these files?" |
| An assumption written as fact | A scope phrase such as "for asynchronous messaging between services" that nobody stated | Tag it `[Assumed: ...]` or ask. |
| Old ADR rewritten | Body of the superseded ADR changed | Change only its status line. |
| Invented second option or downside | "We also considered X" with no source | Remove it. Write the one-option sentence or a tag. |
| New file only | Index, superseded status line or RFC link missing | Plan the whole change (step 5). |

More anti-patterns with symptoms and fixes: `references/anti-patterns.md`.

## Files in this skill

- `templates/adr-default.md`: default template when the repository has none.
- `templates/adr-short.md`: short variant for small decisions.
- `references/formats.md`: formats, status words, paths, numbering, thresholds and tools compared.
- `references/anti-patterns.md`: anti-patterns for writing and for reviewing ADRs.
- `references/reviewer-prompt.md`: prompt for the fresh reviewer subagent.
- `references/sources.md`: sources this skill is based on.
