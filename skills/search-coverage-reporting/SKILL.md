---
name: search-coverage-reporting
description: Use when answering a question about a codebase by targeted search (grep/glob/read) - requires stating what was NOT examined, so an incomplete answer cannot pass as a complete one.
---

# Search Coverage Reporting

Targeted search is the cheapest way to answer a question about code. Its one
defect is that it is **silently incomplete**: search stops as soon as it has an
answer, and nothing in the output shows what was never looked at.

This skill fixes that with one rule.

## The rule

When you answer a code question using search, end the answer with a coverage
note:

```
Coverage: searched <what>. Read <n> files: <list>.
Not examined: <what you knowingly skipped, and why>.
Confidence: <high|medium|low> per claim, with inferred claims marked.
```

A reader can then judge the answer. Without it, four findings out of seven look
identical to seven out of seven.

## Why this matters (measured)

In a controlled comparison on two coupled repositories — one producing data
tables, one consuming them — the same question was answered three ways with the
same model:

| Method | Cost | Result |
|---|---|---|
| targeted search | cheapest | 4 of 7 data flows found |
| whole-repo flat export | ~1.4x tokens, ~2.6x wall clock | 7 of 7 found |
| pre-built code graph | middling | 7 rows, but most unverified |

Search was not wrong. It was incomplete, and only the arm that marked its own
rows "inferred" made that visible. The arms that sounded certain were less
useful than the arm that admitted doubt.

## When to escalate instead of search

Classify the question first. It is cheap and it decides the method.

**Depth question** — one subsystem, precise answer.
*"Why does this function fail on empty input?", "Which library does this module
use?", "Where is this value set?"*
→ Targeted search. Add the coverage note and stop.

**Breadth question** — contracts, mappings, audits, inventories.
*"What talks to what?", "Map the data flow between A and B", "List every place
that writes this table", "Is anything unused?"*
→ Do **not** trust a first search pass. Either sweep exhaustively (enumerate the
candidate set first, then check every member) or load the whole relevant source
at once. Completeness is the deliverable here, so stopping early defeats the
task.

Unsure? Treat it as breadth. The asymmetry is decisive: over-searching costs a
bounded amount of extra tokens, while under-searching costs an unknown number of
missing findings, and you cannot tell from the output that they are missing.

## Enumerate before you conclude

For any breadth question, build the candidate list **before** answering, from a
source that is complete by construction:

- every file matching a glob, not the first few interesting hits
- every model/table/endpoint declared in a manifest or config
- every member of a directory, then mark each one checked or skipped

Then answer per candidate. "I found three" is a claim about your search;
"three of the eleven candidates match, here are the other eight" is a claim
about the code.

## Read the contract files

Breadth answers usually live in declarative files nobody thinks to grep for:
schema definitions, interface definitions, DDL, API specs, dependency
manifests, generated documentation. Open them explicitly. A search driven by
identifiers found in application code will not surface them, because the
question's words do not appear there.

## Say when the answer cannot exist in the code

Some couplings are not statically visible at all. A common example: a consumer
builds a resource name at runtime from configuration held outside every
repository, so no static tool can verify which producer it points at. When that
is the case, say so as the finding — do not present a guessed binding as an
observed one.

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| Answer with no coverage note | Add the note; it costs two lines |
| "I searched the codebase" | Name the patterns and paths actually searched |
| Confident prose on inferred facts | Mark inferred claims as inferred |
| Breadth question, first-hit answer | Enumerate candidates, then check each |
| Skipping schema/spec files | Open contract files explicitly |
| Guessing a runtime binding | Report it as unresolved |
