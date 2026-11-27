---
name: writing-rfcs
description: >
  Use when a technical choice is still open and people must comment before a
  human decides: write, draft, revise or close an RFC (request for comments),
  design proposal, technical proposal, RFD, KEP or PEP style document ("write
  up a proposal", "should we split this service", "propose moving from REST to
  gRPC"). Also use when an RFC is asked for but the change may be too small or
  already decided, to route it. Not for recording a decision that is already
  made (use writing-adrs), not for small easy-to-undo changes (PR
  description), and not for API reference docs, READMEs, how-to guides or
  requirements documents.
---

# Writing RFCs

An RFC (request for comments) proposes a change and asks people for feedback
**before** the decision is made. Its job is to move open decisions to
"decided" through a human process. The agent prepares that step. It never
takes it.

So the unit of work is the **decision**, not the template section. The
template is the last step: it renders what the agent found out.

## When to use which document

Route first. This table is the same in the `writing-adrs` skill.

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

"Hard to undo" is also called a one-way door. "Easy to undo" is a two-way
door.

**If the user asks for an RFC but the table says PR description:** say so in
one or two sentences, then give the PR description text (what changed, why,
test plan). Do not also write the RFC. Offer the short RFC template in one
line, in case they still want it.

**If the user asks for an RFC but the decision is already made:** say that an
RFC asks for feedback before a decision, and switch to writing-adrs. If the
user says the decision is still open after all, continue here.

## Rules shared with writing-adrs

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
For an RFC: the options may still be open, because that is what reviewers
comment on. Stop and reply "not ready", with what is missing, only when you
cannot name the problem, or cannot name at least one option that could solve
it besides "Do nothing".

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

### 1. Find the decisions

Before any prose, list the decisions at stake. Show this list in your reply.

| Decision | State (open / settled) | Undo cost (one-way / two-way) | Scope (one team / several) |
|---|---|---|---|

Pick the document from this list with the routing table above.

### 2. Check the timing

Search git history, branches and open PRs for code that already does what the
proposal says. If the change is already built or merged, tell the user. Then
either route to writing-adrs or a PR description, or label the document
"Record, written after implementation". Do not present it as a request for
comments.

### 3. Find the repo's format

Search for existing RFC, design-doc, RFD and ADR folders, templates and front
matter (for example `docs/rfcs/`, `rfcs/0000-template.md`, `rfd/NNNN/README.adoc`,
`doc/adr/`, `design/`). Also check whether a loaded skill or the repo's
instructions define a format. Then follow **Format** above:

- A format exists: use it, its numbering, its file name pattern and its
  status names. Tell the user which file you based this on.
- No format exists: use `templates/rfc-full.md` or `templates/rfc-short.md`.

Even in a repo format, keep the required slots from step 6 (owner, approvers,
review deadline, feedback needed, Decision, ADRs to write). Add them as extra
fields if the format has none.

### 4. Ground every claim

Read the code, CODEOWNERS and related ADRs/RFCs the proposal touches. Check
what the user says about the current system against the code. Each claim
about the current system cites its source: a file path, a user statement, or
a linked document.

Mark each statement a reviewer could challenge:

- **[Decided]** the user said it, or a linked record settles it.
- **[Assumed: ...]** and **[Open: question]** as defined in **Tags** above.

### 5. Ask

Follow **Missing context** above. Do not spend questions on the owner, the
approvers, the comment period or the location: use placeholders for them
unless the user already said.

### 6. Draft

Fill the template. These slots are required in every RFC, also in the short
one:

- **Status:** `draft`.
- **Decision owner** and **Approvers:** as in **Decider model** above. You may
  list CODEOWNERS teams as a suggestion tagged `[Assumed: ...]`.
- **Consulted:** affected teams or roles. Their advice does not block.
- **Review deadline / comment period:** a date the user gave, or
  `<DEADLINE: to be set, suggest 1 week>`.
- **Feedback needed:** one line that says what reviewers should answer.
- **Goals** and **Non-goals** (non-goals are things a reader could expect,
  but that are out of scope).
- **Alternatives:** a labelled "Do nothing" option with its cost, and every
  other option that could really solve the problem. Each option has at least
  one downside and a reason it was not chosen.
- **Drawbacks:** answers "why should we not do this?". Never empty.
- **Open questions** in three groups: before acceptance, during
  implementation, out of scope.
- **Decision:** empty until a human states the outcome (see Close below).
- **ADRs to write:** one line per open decision from step 1. This is the
  last section of the document.

Leave out an optional section that has no real content. Do not fill it to
look complete. If a core section has no content, write it as an
`[Open: ...]` question instead.

If only one option besides "Do nothing" is viable, say so and explain why. Do
not add a weak option to make the list look balanced.

### 7. Reader test with a fresh subagent

Start a fresh subagent that sees only the draft, not this conversation. Ask
it to:

1. list 5-10 questions a reviewer will ask, each marked blocker or remark;
2. answer "why should we not do this?" from the text;
3. name any statement that looks like a fact but has no source or tag;
4. name the decisions and the deadline, as a reviewer would.

Fix the gaps it finds. Report to the user the count of pro and con points per
option.

### 8. Self-check, then hand over

Run the self-check below. Then show the draft in the reply. **Write no file
before the user approves the draft.** After approval, write it at the path
the repo format gives.

## Hard rules

- Status stays `draft` (see **Status** above). The agent never sets
  `accepted`, `approved`, `implemented` or any final status.
- Never invent names, approvers, consensus, prior discussions, incidents,
  numbers, benchmarks, dates or context. Use a placeholder or a tag.
- Format: see **Format** above.
- Show the draft first. Write files only after user approval.
- Mark every challengeable statement [Decided], [Assumed: ...] or [Open: ...].

## Self-check before handover

- [ ] Decision list shown, and the document type matches the routing table.
- [ ] Timing checked: no implementation already merged, or it is said.
- [ ] Format source named (repo file, loaded skill, or this skill's default).
- [ ] Status is `draft`. Owner, approvers, deadline are names the user gave
      or visible placeholders.
- [ ] "Feedback needed" line present.
- [ ] Goals and Non-goals present.
- [ ] "Do nothing" listed by name, with its cost.
- [ ] Every option has at least one downside. No option is there only to lose.
- [ ] Drawbacks not empty. Rollout, rollback and monitoring covered.
- [ ] No number, name or incident without a source or a tag.
- [ ] Open questions split into three groups.
- [ ] Decision section present and empty.
- [ ] Document ends with "ADRs to write", one line per open decision.
- [ ] No leftover template text. No section kept only for the template.
- [ ] Short RFC at most ~3 pages. Full RFC warns and suggests a split above
      ~10 pages.
- [ ] Not more than 3 questions to the user.
- [ ] Reader subagent ran, and its gaps are fixed.
- [ ] No file written yet.

## Revising and closing

**Revise.** Use **Review rounds** above.

**Close.** Only when a human states the outcome in the conversation
(accepted, rejected, withdrawn, postponed). Fill the Decision section: the
outcome, who decided, the date and the reasons, also for a rejected RFC. If
accepted, end your reply with the "ADRs to write" list and offer to draft
them with writing-adrs. Each ADR links back to the RFC's Decision section and
starts as `proposed`, not accepted. After acceptance, do not change the RFC
much: a bigger change goes into a new RFC or an addendum, with a note on the
original.

## Common mistakes

These come from tests of agents without this skill.

| Mistake | Fix |
|---|---|
| Header has "Author" and "Owning team", but no decision owner and no approvers | Use the required slots in step 6, with placeholders |
| No Goals and no Non-goals sections | Both are required slots |
| Only a "decision needed by" date; no comment period; reviewers do not know what to answer | Add "Review deadline" and "Feedback needed" |
| RFC raises several decisions but names one future ADR, or none | End with "ADRs to write", one line per open decision |
| User asks for an RFC for a small rename; agent says a PR description fits better, then writes the full RFC anyway | Follow the routing table: give the PR description text, offer the short RFC in one line |
| Alternatives are variants of the proposal; "do nothing" is not named | Add a labelled "Do nothing" option with its cost |
| Wrong reference style (for example "ADR 6" where the repo writes "ADR 0006") | Copy identifiers exactly as the repo writes them |
| Status set to "Accepted" because the user said "we decided" | That is an ADR case. In an RFC, status is `draft` until a human states the outcome |
| Polished, long document written after the code exists | Check timing in step 2. A rough early draft is the right output |
| Every section filled, many arguments for the chosen option, few against | Cut every sentence that would not change a reader's mind. Count downsides per option |

Keep what agents already do well: they mark gaps instead of inventing facts,
they cite files they read, they keep the draft short, and they show it before
writing a file.

## Reference files

- `templates/rfc-full.md` - default full template.
- `templates/rfc-short.md` - short template for two-way, one-team changes.
- `references/anti-patterns.md` - failure modes with symptoms and fixes.
- `references/format-comparison.md` - known RFC formats, status models,
  decision models, comment periods.
- `references/sources.md` - sources this skill is based on.
