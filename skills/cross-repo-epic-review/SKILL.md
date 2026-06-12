---
name: cross-repo-epic-review
description: >
  Use when conducting a code review of a multi-repo epic or cross-team feature.
  Covers the four-round structure that catches what single-pass agent reviews
  miss: branch state, cross-repo contract drift, strategic framing gaps, and
  epic scope creep.
---

# Cross-Repo Epic Review — Four-Round Structure

A single review pass on a multi-repo epic misses too much. Agent reviews miss
cross-repo consistency. Flat-source reviews miss branch state. Neither catches
strategic framing issues. This four-round structure closes those gaps.

---

## When to use

- Epic spans 2+ repos with shared contracts, interfaces, or schemas
- You need confidence before a major integration milestone or go-live
- A previous review surfaced inconsistencies but couldn't pinpoint root cause
- Stakeholders disagree on whether the epic should stay unified or split

---

## Round 1a — Agent audit (parallel, one agent per repo)

**Best for:**
- Branch state ("is this merged or still WIP?")
- File-context questions ("does repo B implement the interface repo A expects?")
- Repo-specific scaffolding completeness
- Recent commit history and open PRs

**How to run:**

Spawn one agent per repo in parallel. Give each agent:
- The repo path
- The epic ticket ID and a one-paragraph description of what it's supposed to do
- A checklist of questions specific to that repo

Each agent is blind to what the others find — that's intentional. Diversity
surfaces more than coordination.

```
parallel agents:
  Agent(repo=repo-a, prompt="Review <EPIC_ID> scope in repo-a. Check: ...")
  Agent(repo=repo-b, prompt="Review <EPIC_ID> scope in repo-b. Check: ...")
  Agent(repo=repo-c, prompt="Review <EPIC_ID> scope in repo-c. Check: ...")
```

**What agents miss:** cross-repo grep ("where else does this enum appear?"),
contract consistency across repo boundaries, hardcoded values that diverge.

---

## Round 1b — Flat-source review (repo2ai dump → independent reviewer)

**Best for:**
- Cross-repo grep-style questions ("where else is this constant defined?")
- Shared interface mismatches
- Hardcoded enum drift across repos
- Any "does X in repo A match X in repo B?" question

**How to run:**

```bash
repo2ai /path/to/repo-a --output /tmp/repo-a.md
repo2ai /path/to/repo-b --output /tmp/repo-b.md
cat /tmp/repo-a.md /tmp/repo-b.md > /tmp/combined.md
```

Feed the combined dump to a fresh reviewer with cross-repo questions.
The reviewer sees everything as one flat document — no repo boundary blindness.

Run **in parallel with Round 1a** — same wall-clock cost as a single pass.

---

## Rounds 1a + 1b synthesis

Before moving to Round 2:

1. Merge findings from both passes
2. Flag contradictions between rounds
3. **Cross-check ~25% of contradictions against current file state** — a
   significant fraction are stale findings from old snapshots. Verify before
   acting.

---

## Round 2 — Strategic framing (epic document review)

**Best for:** Issues agents reliably miss.

Agents default to technical findings. A separate pass on the epic *document*
(spec, RFC, ADR) catches:

| Issue type | What it looks like |
|---|---|
| Technology age-shaming | "Legacy X must be replaced" without evidence it's a bottleneck |
| False binary | "Either we rewrite or we're stuck" when a third path exists |
| Mandate inflation | Scope quietly grew from PoC to production requirement |
| Missing success criteria | No definition of "done" or "working" |
| Decision-owner gaps | Key architectural choices attributed to "the team" with no owner |
| Political surface | Language that will alienate a stakeholder who needs to sign off |

**How to run:**

Give a reviewer the epic document plus this checklist. This is a distinct
cognitive mode from technical review — prime explicitly:

```
Review this epic for strategic and framing issues, not technical correctness.
Flag: false binaries, missing success criteria, undefined owners, scope drift,
and any language likely to cause pushback from <stakeholder type>.
```

---

## Round 3 — Epic-split test

**Best for:** Epics with maturity ladders (PoC → Pattern → Platform,
or M0 → M1 → M2) where scope creep risk is high.

Ask: should this be **phases inside one epic** or **three separate epics with
explicit triggers**?

**Signs it should split:**
- Phase 1 ("PoC") would be shippable and valuable on its own
- Phase 2 trigger is unclear — "when Phase 1 is done" is not a trigger
- The team treats Phase 1 as a throwaway ("Wegwerf-PoC") but Phase 2 secretly
  assumes its output is production-grade
- Stakeholders have different mental models of where the epic ends

**Signs it should stay unified:**
- Phases are tightly coupled — Phase 2 requires rework of Phase 1 internals
- The deliverable is only valuable when all phases complete
- All phases have a single owner team

If it splits: define the trigger conditions (business event, metric threshold,
explicit decision gate) before writing the child epics. Splits without triggers
just defer the scope conversation.

---

## Cost model

| Round | Who runs it | Wall-clock time | What it catches |
|---|---|---|---|
| 1a | Parallel agents | ~10 min | Branch state, repo-local completeness |
| 1b | Single agent on dump | ~10 min (parallel with 1a) | Cross-repo consistency |
| 2 | Single agent or human | ~5 min | Strategic framing gaps |
| 3 | Single agent or human | ~5 min | Scope creep, split decision |
| **Total** | | **~20 min wall clock** | |

Rounds 1a and 1b run in parallel — total wall-clock is max(1a, 1b), not sum.

---

## Common mistakes

| Mistake | What you miss |
|---|---|
| Agents aware of each other's findings | Findings converge prematurely; blind spots shared |
| Skipping Round 2 | Mandate inflation, false binaries slip through to implementation |
| Splitting epic without trigger conditions | Scope conversation deferred, not resolved |
| Acting on all contradictions immediately | ~25% are stale — verify current file state first |
| Using same prompt for Round 2 as Round 1 | Agent stays in technical mode; misses framing issues |
