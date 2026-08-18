---
name: agent-memory-hygiene
description: >
  Use when deciding when and how to commit items to a project memory system.
  Covers session boundary definitions, item quality rules, and the tradeoff
  between over-committing (noise) and under-committing (lost learnings).
---

# Agent Memory Hygiene

## The core tradeoff

**Over-committing** makes noise, degrades retrieval — future sessions
surface false matches, spend tokens on irrelevant context.

**Under-committing** loses learnings forever — next session re-derives
same thing from scratch.

Goal: commit at right granularity so system gets smarter over time,
no garbage buildup.

---

## When to commit

### Do commit

- **Session boundary** — end of meaningful work block: PR merged, epic
  done, debugging session resolved, major decision made
- **Hard-won lesson** — took 30+ minutes to figure out, would
  take same time again
- **Non-obvious gotcha** — tool flag, API behavior, or failure mode
  not in official docs
- **Decision rationale** — why an architectural choice was made (code shows
  *what*, memory preserves *why*)

### Do not commit

- After every individual git commit — commit message's job
- Ephemeral task state ("currently working on X") — belongs in task tracking,
  not memory
- Things already documented in codebase or official docs
- Intermediate investigation steps that led nowhere

**Rule of thumb:** if you'd write it in commit message → git.
If you'd write it in an ADR → memory.

---

## Session boundary pattern

```
Session start  → seed context (load relevant past learnings)
  ↓
Work block     → code, debug, research, decide
  ↓
Session end    → commit episode (record what was learned, decided, left open)
```

Do not run commit step after every sub-task within a session. One commit
per session boundary = right cadence for coding-heavy work.

---

## Item quality rules

Memory item lacking metadata = invisible to retrieval. Always populate:

| Field | Why it matters | Example |
|---|---|---|
| `repos[]` | Enables repo-filtered lookup | `["owner/service-api", "owner/infra-tf"]` |
| `tags[]` | Tag-based recall filtering | `["aws", "auth", "gotcha"]` |

Items missing both fields = reachable only by full-text search — slow,
imprecise, skipped by most retrieval paths.

**Graph links are a separate call, not a write field.** No create/commit/supersede
tool takes a `related_keys` argument. Write the item first, then link the returned
key: a generic `link_items(source_key, target_keys, relation_type=)` call for
item-to-item edges, or a reference-linking call for source/evidence attachment.
Unlinked items are valid — link when a relationship is real, not to fill a field.

**Do not rely on repo inference.** Passing `repos` at all disables inference
entirely, and inference itself only matches full forge URLs
(`github.com|gitlab.com|bitbucket.org/<owner>/<repo>`) — bare repo names in prose
are never picked up. Always pass `owner/repo` form explicitly, or repo-filtered
lookup splits across two spellings of the same repo.

---

## Memory item types and their cadence

| Type | What it captures | Cadence |
|---|---|---|
| **Unit / episode** | Specific session learnings, task outcomes | Every session boundary |
| **Concept** | Synthesized pattern across multiple sessions | Deliberate, reviewable — not automatic |
| **Project summary** | Breadth-first state of the project | After major milestones, not routine commits |

**Concept synthesis = explicit act, not auto-generated.** System may
propose consolidations, but agent creates concepts deliberately after
reviewing what would be synthesized. Automatic concept creation makes
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

- Retrieval returns many items irrelevant to query
- Sessions load same stale context repeatedly
- Concepts contradict each other (one supersedes other but wasn't marked)
- Items exist without repos/tags — invisible to primary retrieval
- Items were never linked after creation, so the graph is all islands

**Fix:** periodic review pass. Archive superseded items. Add missing metadata.
Merge near-duplicate units into a concept. Smaller, well-linked graph
beats large, sparse one.

---

## Signs of under-committed memory

- Team re-discovers same gotcha across sessions
- Architectural rationale exists only in chat history (lost on context reset)
- New contributors ask questions memory should answer

**Fix:** lower bar for unit-level commits. Short, specific, tagged. A
three-sentence learning with proper repos/tags, linked afterwards, beats
a long, untagged narrative.
