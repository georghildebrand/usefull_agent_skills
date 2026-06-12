---
name: agent-memory-hygiene
description: >
  Use when deciding when and how to commit items to a project memory system.
  Covers session boundary definitions, item quality rules, and the tradeoff
  between over-committing (noise) and under-committing (lost learnings).
---

# Agent Memory Hygiene

## The core tradeoff

**Over-committing** creates noise that degrades retrieval — future sessions
surface false matches and spend tokens on irrelevant context.

**Under-committing** loses learnings permanently — the next session re-derives
the same thing from scratch.

The goal: commit at the right granularity so the system gets smarter over time
without accumulating garbage.

---

## When to commit

### Do commit

- **Session boundary** — end of a meaningful work block: PR merged, epic
  completed, debugging session resolved, major decision made
- **Hard-won lesson** — something that took 30+ minutes to figure out and would
  take the same time again
- **Non-obvious gotcha** — a tool flag, API behavior, or failure mode that
  isn't in the official docs
- **Decision rationale** — why an architectural choice was made (the code shows
  *what*, memory preserves *why*)

### Do not commit

- After every individual git commit — that's the commit message's job
- Ephemeral task state ("currently working on X") — belongs in task tracking,
  not memory
- Things already documented in the codebase or official docs
- Intermediate investigation steps that didn't lead anywhere

**Rule of thumb:** if you'd write it in a commit message, it goes in git.
If you'd write it in an ADR, it goes in memory.

---

## Session boundary pattern

```
Session start  → seed context (load relevant past learnings)
  ↓
Work block     → code, debug, research, decide
  ↓
Session end    → commit episode (record what was learned, decided, left open)
```

Do not run the commit step after every sub-task within a session. One commit
per session boundary is the right cadence for coding-heavy work.

---

## Item quality rules

A memory item that lacks metadata is invisible to retrieval. Always populate:

| Field | Why it matters | Example |
|---|---|---|
| `repos[]` | Enables repo-filtered lookup | `["service-api", "infra-tf"]` |
| `tags[]` | Tag-based recall filtering | `["aws", "auth", "gotcha"]` |
| `related_keys[]` | Links items into a graph; prevents discovery islands | keys of adjacent concepts |

Items without all three fields are reachable only by full-text search — slow,
imprecise, and skipped by most retrieval paths.

---

## Memory item types and their cadence

| Type | What it captures | Cadence |
|---|---|---|
| **Unit / episode** | Specific session learnings, task outcomes | Every session boundary |
| **Concept** | Synthesized pattern across multiple sessions | Deliberate, reviewable — not automatic |
| **Project summary** | Breadth-first state of the project | After major milestones, not routine commits |

**Concept synthesis is an explicit act, not auto-generated.** The system may
propose consolidations, but the agent creates concepts deliberately after
reviewing what would be synthesized. Automatic concept creation creates
authoritative-looking but shallow entries.

---

## What belongs in memory vs other systems

| Content type | Where it goes |
|---|---|
| Why an architectural decision was made | Memory (episode or concept) |
| Tool gotcha, non-obvious flag | Memory |
| Current task breakdown and progress | Task tracking (not memory) |
| Temporary investigation state | Conversation context (not memory) |
| Project conventions, code standards | CLAUDE.md / AGENTS.md |
| Repeatable workflow across projects | Skill file |
| What changed in a commit | Git commit message |
| Design rationale for a specific PR | PR description |

---

## Signs of unhealthy memory

- Retrieval returns many items that aren't relevant to the query
- Sessions load the same stale context repeatedly
- Concepts exist that contradict each other (one supersedes the other but wasn't marked)
- Items exist without repos/tags/related\_keys — invisible to primary retrieval

**Fix:** periodic review pass. Archive superseded items. Add missing metadata.
Merge near-duplicate units into a concept. A smaller, well-linked graph
outperforms a large, sparse one.

---

## Signs of under-committed memory

- Team re-discovers the same gotcha across sessions
- Architectural rationale exists only in chat history (lost on context reset)
- New contributors ask questions the memory should be able to answer

**Fix:** lower the bar for unit-level commits. Short, specific, tagged. A
three-sentence learning with proper repos/tags/related\_keys is more valuable
than a long, untagged narrative.
