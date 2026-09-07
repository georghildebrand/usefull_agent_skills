---
name: agent-implementation-gang
description: Use when a software project needs several agents working in parallel with clear ownership, human decision boundaries, verification gates, model capability tiers per role, a code and test budget, and a durable worklog that lets a fresh session resume without chat history. Not for single-file edits or unbounded autonomous implementation.
---

# Agent Implementation Gang

Run an agentic software project as a small, evidence-driven delivery team. One
orchestrator owns scope, integration, the gates and the worklog. Specialist agents
own only their assigned slice. A human owner keeps authority over product direction
and over any change that is hard to reverse.

## When to use

Use it when at least two of these are true:

- the work needs more than one agent, or more than one session;
- several agents may touch the repository at the same time;
- a human must approve something before it becomes real;
- "is it done" needs evidence, not a claim.

Do not use it for a one-file edit, a quick bug fix, or a request to "just build
the whole thing autonomously".

## Operating model

- Work packages are small, outcome-shaped and independently verifiable.
- Proposal, evidence, implementation, verification and approval stay separate.
- Green tests are evidence of correctness, never product acceptance.
- A specialist implements only inside an explicit owned path and contract.
- An independent read-only critic is the last correctness gate.
- An append-only worklog is the only durable state. Chat context is not state.
- Every package is budgeted: smallest change that satisfies the contract, tests that
  cover the risk rather than the lines.

## Roles

Five roles are always present:

| Role | Owns | May decide |
| --- | --- | --- |
| Orchestrator | Bounding work, dispatch, integration, gates, worklog | Whether evidence is sufficient. Not scope, not approvals |
| Architect | Work packages and interface contracts | Proposed boundaries and sequencing |
| Implementer (one per package) | The package's owned paths and its focused tests | Local implementation choices |
| Verification Critic | Read-only review and test runs | PASS / FAIL only. Never edits |
| Human owner | Product direction and real approvals | Final scope and production authority |

Add specialists only when the project actually needs them, for example a domain or
schema steward, a UI engineer, a data-ingestion engineer, or a second-model
refinement reviewer. Each added role gets its own owned paths.

Two rules that keep this safe:

- **One owner per path.** Two agents must never hold write access to the same file
  in the same round. The orchestrator keeps the current path-to-owner list in the
  worklog checkpoint, hands out the locks, and integrates. Specialists do not.
- **Critics never edit.** A critic that fixes what it found has stopped being an
  independent gate.

Each role also has a model capability tier. See **Model tiers** below.

## Model tiers

Pick models by capability tier, never by name. Names change; the tiers do not.

| Tier | Means | Use for |
| --- | --- | --- |
| **High reasoning** | Strongest available model, extended thinking on | Architecture and work-package decomposition; the verification critic; the refinement review; any decision that is hard to reverse |
| **Medium** | Solid coding model, normal thinking | Implementation inside an already-defined contract; focused tests; the handoff report |
| **Low / fast** | Cheapest usable model | Read-only retrieval, memory lookups, log and grep sweeps, mechanical edits such as renames, formatting and boilerplate |

Suggested assignment:

| Role | Tier | Why |
| --- | --- | --- |
| Orchestrator | High | Judges whether evidence is sufficient. That is the judgment the whole gate rests on |
| Architect | High | A wrong boundary costs more than a wrong line of code, and is found much later |
| Implementer | Medium | The contract already made the hard decisions. Raise to high for genuinely novel or concurrency-heavy work |
| Verification Critic | High, never below the implementer | See the rule below |
| Refinement reviewer | High, different model family | A second opinion only works if it is genuinely independent |
| Retrieval / memory subagent | Low | Bounded lookups returning structured findings. Spending a high tier here buys nothing |
| Mechanical worker | Low | No judgment involved. If judgment appears, it was the wrong tier |

### Rules

- **The critic is never weaker than the implementer.** A weaker critic cannot find
  what a stronger model wrote, so it approves by default. This turns the gate into a
  rubber stamp, which is worse than no gate, because it produces false confidence.
- **Independence needs a different family, not just a different tier.** Two models
  from the same family share blind spots. Use a different family for the second
  opinion, and keep it read-only.
- **Reasoning effort is a separate knob from tier.** A high tier at low effort is not
  a high-reasoning review. Turn effort up for critics and architecture, down for
  mechanical fan-out.
- **Downgrade breadth, not gates.** When cost matters, cut the number of parallel
  finders or the scope of a sweep. Never cut the tier of a correctness or security
  gate.
- **Record the tier in the worklog.** A `passed` from a low tier is weaker evidence
  than a `passed` from a high tier. A later session must be able to tell them apart,
  and to decide whether to re-run the gate.

## Start or resume protocol

Before changing any code:

1. Read the project operating guide and the implementation contract.
2. Resolve the workstream in the preferred memory manager, to recover prior
   decisions, learnings and open todos.
3. Read the worklog backwards until the newest **Resume checkpoint** is fully
   understood. On any conflict with memory, the worklog wins on current state.
4. Identify: active work package, current gate, current owner, protected paths,
   last known-good verification.
5. Inspect only the relevant code. Do not edit a path another active agent owns.
6. State the bounded objective, owned files, non-goals, verification plan and the
   required handoff before dispatching or implementing.
7. Run the baseline verification when one exists and is cheap enough.
8. The orchestrator appends a worklog entry after every meaningful block, gate
   change, handoff or newly found blocker.

The newest checkpoint is authoritative. Never infer completion from an old plan, a
previous chat, or a green test run alone.

## Work package contract

Every work package states:

- outcome and user-visible value;
- in scope, and explicitly out of scope;
- owned paths, and paths that must not be touched concurrently;
- stable interface and data contracts;
- invariants and trust boundaries;
- exact verification commands and acceptance criteria;
- a rough size bound, and which behaviours need a test;
- the model tier for the implementer, and for the critic;
- next handoff role.

If a contract is missing, define the smallest explicit contract, flag it, and stop
there. Do not silently absorb another role's scope.

## Code and test budget

A gang inflates a codebase faster than a single developer, and for a structural
reason: every parallel agent solves its slice in isolation, so each one writes its
own helper, its own config flag and its own test fixture. Nobody sees the duplication
because nobody sees the whole diff. Budget for this from the start.

### Code

- Write the smallest change that satisfies the contract. Nothing speculative.
- No abstraction for a single use site. Two use sites is a coincidence; three is a
  pattern.
- No configuration knob nobody asked for. A hard-coded value that is easy to find
  beats a setting that must be documented, tested and migrated.
- No error handling for situations that cannot occur.
- Prefer deleting code over adding code. A package that removes more than it adds is
  a good package, not a suspicious one.
- Before writing a helper, search for an existing one. In a gang this is not optional:
  the helper you need was probably written by another agent this morning.

### Tests

- Test the contract and the risk, not the lines. Coverage percentage is not the goal.
- One test per behaviour, not one per function. Three assertions in one clear test
  beat three near-identical tests.
- Test the boundary cases that can actually happen: empty, missing, conflicting,
  concurrent. Skip the impossible ones.
- No test that only restates the implementation. If it cannot fail for a real reason,
  it is maintenance cost with no return.
- One regression test per fixed bug. That one always earns its place.

### Enforcement

- The handoff reports lines added and removed, and the number of tests added. A large
  diff is allowed, but must be justified in one sentence.
- The critic checks for excess as well as for correctness: duplication with existing
  code, unused abstraction, tests that cannot fail, a knob nobody requested. Excess is
  a finding, not a style opinion.
- The orchestrator deduplicates at integration. That is the only point where the
  whole diff is visible, so it is the only place the duplication can be caught.
- Reducing size never justifies removing a test that covers a real risk, or a safety
  boundary. Cut volume, not protection.

## Handoff report

Every specialist finishes with:

1. Outcome, and files changed.
2. Size: lines added, lines removed, tests added. One sentence of justification if
   the diff is large.
3. Exact verification commands, and their real output.
4. Decisions made inside the package.
5. Risks, unknowns, deferred work.
6. Recommended next specialist.

## Worklog contract

**The orchestrator maintains the worklog.** It is the orchestrator's single
non-delegable duty: no gate change, handoff or blocker exists until it is written
down. A specialist reports its handoff to the orchestrator, which appends the entry.
A specialist may append its own entry only when it is running unsupervised, and it
still reports the same content back.
Keep one append-only worklog file, for example `docs/WORKLOG.md`. Fix factual
mistakes with a dated correction entry. Never rewrite past evidence. Never record
credentials, tokens, secrets, personal data, or private chain-of-thought.

Use this entry template verbatim so any session can parse it:

```markdown
## <YYYY-MM-DD> — <WP-ID> — <short objective>

**Roles:** <orchestrator / implementer / critic ...>
**Model tiers:** <role: high | medium | low, per role that acted>
**Changed:** <files and capabilities>
**Size:** +<lines> / -<lines>, <n> tests added
**Decisions:** <what was decided, and why>
**Assumptions:** <what was assumed, and what would falsify it>

**Verification**
```
<exact command>
<exact result>
```
**Gate:** <planned | in_progress | blocked | failed | pending | passed | complete>

**Risks / blind spots:** <...>
**Deferred:** <...>

### Resume checkpoint
- status: <one of the gate values above>
- last known-good verification: <command + when it last passed, and at which tier>
- active owner: <role>
- next action: <one concrete action>
- do not edit concurrently: <paths>
```

## Memory management

The gang uses two stores, and they are not interchangeable.

| Store | Lives in | Authoritative for | Lifetime |
| --- | --- | --- | --- |
| Worklog | The repository, append-only | Current gate, owner, next action, verification evidence | This project |
| Memory manager | The user's preferred memory or knowledge tool, outside the repository | Cross-session and cross-project context, decisions, precedent, open todos | Many projects |

The worklog answers "where exactly are we in this package". The memory manager
answers "what did we already learn, decide, or reject, possibly months ago". Do not
copy one into the other wholesale. Duplicated state drifts, and then the two
disagree.

### Rules

- **Resume reads memory first, then the worklog.** Memory gives the topic and the
  history. The worklog gives the exact resume checkpoint. The worklog wins on any
  conflict about current state, because it sits next to the code.
- **Bind a focus topic before writing items.** Register the workstream in the memory
  manager under a stable session identifier, so later "continue <topic>" resolves to
  the same session instead of creating a new one.
- **Read-only retrieval is delegated.** Multi-step lookups go to a cheap retrieval
  subagent that returns structured findings. Writes and synthesis stay with the
  orchestrator.
- **Write at session boundaries, not per commit.** One episode per meaningful work
  block. Writing after every single commit produces noise that buries the signal.
- **Every item carries repository names and a small number of tags.** Items without
  them are invisible to the normal retrieval paths, which makes them worthless later.
- **Durable follow-up work becomes a tracked todo**, not a line buried in prose.
- **The confidentiality boundary applies to memory writes too.** Secrets, credentials
  and personal data never go in. Filter out personal remarks about people before
  anything is written that a colleague may later read.

### What each store gets

Worklog entry, at every block: gate, owner, next action, exact verification output,
model tier of each acting role, paths locked.

Memory episode, at session close: what the block achieved, decisions and the reason
behind them, learnings that will still matter in three months, open questions, and
concrete todos.

Skip the memory write for a trivial or purely mechanical block. The worklog entry is
still mandatory.

See the companion skill `agent-memory-hygiene` for the detail on item quality and on
where a session boundary actually falls.

## Verification flow

For any non-trivial package:

```text
architecture / domain contract
  -> implementer
  -> focused tests and project checks
  -> independent read-only verification critic
  -> fix evidenced findings
  -> rerun all affected checks, and the critic
  -> optional refinement / compression review pass
  -> owning implementer applies accepted refinements
  -> rerun gates, update worklog
```

The critic's job is to disprove claims, not to confirm them. Standard attacks:

- the claim of completion rests on a test that does not exercise the changed path;
- a decision reserved for a human can be made, or bypassed, by an agent;
- missing or unreadable evidence is being treated as "fine";
- the change reaches outside the paths the work package declared as owned;
- the change crosses a boundary the work package explicitly excluded;
- stale state can overwrite a newer decision;
- the verification command reported in the handoff is not the one that was run;
- the package added an abstraction, a config knob or a helper that duplicates code
  which already exists;
- a new test cannot fail for any real reason.

Two principles the critic always applies:

- **Unknown is not safe.** Missing data, a skipped test, or an incomplete run means
  unknown. It never means safe, unaffected, or empty.
- **Nobody grades their own work.** An agent's own claim that a package is done is
  input to the gate, never the gate itself.

## Boundary constraints

Each work package names its own boundaries before implementation starts. The orchestrator asks, and writes the answers into the package:

- which paths may be written, and which must not be touched;
- which external systems may be reached, and which are out of scope;
- where state is allowed to persist, and whether anything temporary is being used
  that must not become permanent;
- which parts must keep working unchanged, and how that is checked.

Hard limits for every agent in the gang, in every package:

- do not read `.env` files, credential stores, keychains, tokens, or unrelated user
  configuration;
- do not commit, push, merge, deploy, delete, or change infrastructure state without
  explicit authorization for that specific action.

## Refinement and code compression

Run a refinement pass only after the primary correctness and security critic
passes. The reviewer is read-only, runs at a high tier in a different model family
(see **Model tiers**), and can never overrule a failed correctness or security gate.
It sorts its output into three lists:

1. product and architecture refinements;
2. correctness, security or regression findings;
3. code-compression candidates.

Code compression means removing duplication and needless indirection while keeping
named domain concepts and every safety boundary intact. It is not minification, not
deleting tests, and not removing context that a future reader needs. The owning
implementer applies accepted changes, then every affected test and critic runs
again.

## Project binding

This skill is generic on purpose. Bind it to a project through that project's own
files, not by editing this skill:

- `AGENTS.md` or `CLAUDE.md` — operating guide, ownership map, hard constraints;
- a gang document — the concrete role list for this project;
- a worklog — durable history and the newest resume checkpoint;
- one work-package document per active package;
- a registered focus topic in the preferred memory manager, using a stable session
  identifier, so a later session can resume the workstream by name.

Never put live project state — current package, test counts, repository paths — in
this skill. It goes stale, and it does not belong in shared documentation.
