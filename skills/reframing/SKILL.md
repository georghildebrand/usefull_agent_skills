---
name: reframing
description: Reframe difficult questions, ideas, decisions, research problems, or projects when progress is blocked by the current problem representation. Use when the user asks to reframe a problem, challenge assumptions, find a better mental model, identify hidden invariants, escape a local optimum, compare alternative problem formulations, or investigate whether the search space itself is wrong. Especially useful when repeated analysis produces more detail but little progress. Do not use for straightforward factual questions or ordinary brainstorming where the current framing is adequate.
---

# Reframing

Treat reframing as search over problem representations, not as brainstorming for more answers.

The objective is to determine whether a different choice of primitives, relations, constraints, invariants, or objective function makes the problem easier to explain, predict, or act on.

## Core principle

Distinguish three levels:

1. **Solution search** — search for better answers inside the current frame.
2. **Representation search** — change how the problem is represented while preserving the underlying observations and constraints.
3. **Frame change** — replace assumptions about what is fundamental when the old representation requires too many exceptions or fails to explain important observations.

Do not call ordinary optimization inside the current frame a reframing.

Example: renaming "microservices" to "components" changes vocabulary, not the frame. Modeling the same deployment problem as a constraint graph — which deploys must never overlap, which invariant each one can violate — changes primitives and relations. That is a reframing.

## Workflow

### 1. Reconstruct the current frame

State the user's current representation as precisely and compactly as possible.

Extract:
- objects or entities considered fundamental;
- relations between them;
- objective or success criterion;
- constraints treated as fixed;
- implicit assumptions;
- observations the frame is meant to explain;
- invariants that should survive any valid reframing.

Separate observations from interpretations. Do not silently convert a user's interpretation into a fact.

When the problem concerns an existing system (codebase, dataset, organization, running service), anchor every claim about that system in checkable evidence: a file path, a measurement, a document, a log line. A frame built on unanchored claims is rejected during evaluation, however elegant it is.

### 2. Look for pressure on the frame

Identify evidence that the current representation may be the bottleneck:
- recurring exceptions or special cases;
- contradictions or unexplained observations;
- growing complexity without improved prediction;
- repeated optimization with little progress;
- sensitivity to arbitrary definitions or boundaries;
- a solution space that appears combinatorially large because the variables may be poorly chosen;
- disagreement caused by different implicit objective functions.

If none of these are present, say that the current frame appears adequate and continue inside it. Do not manufacture a reframing.

### 3. Generate structurally different representations

Construct only a small number of serious alternatives. Prefer representations that change primitives or relations, not vocabulary.

Useful lenses include, when appropriate:
- graph: nodes, edges, topology, reachability, centrality;
- dynamical system: state, transition, attractor, feedback, stability;
- constraint system: invariants, admissible states, forbidden regions;
- optimization: objective, constraints, Pareto frontier, opportunity cost;
- information flow: channel, bandwidth, compression, loss, signal;
- probabilistic model: uncertainty, latent variables, posterior updates;
- game/incentive system: actors, payoffs, strategies, equilibria;
- control system: observable state, control input, feedback, disturbance;
- causal model: interventions, confounders, mechanisms;
- hierarchical model: levels of abstraction, aggregation, emergence;
- representation/invariance view: which transformations should leave the phenomenon unchanged.

Do not force these lenses mechanically. A new frame must alter the structure of the problem.

### 4. Preserve invariants

For each candidate frame, explicitly ask:

> What must remain explainable if this reframing is valid?

Reject frames that gain elegance by discarding critical observations, constraints, historical evidence, or stakeholder requirements.

A useful frame should explain the old successful cases and ideally explain at least one anomaly the old frame handled poorly.

### 5. Apply selection pressure

Evaluate candidate frames by:
- explanatory power;
- number and strength of assumptions;
- ability to explain anomalies;
- predictive consequences;
- falsifiability or testability;
- decision relevance;
- reduction of unnecessary complexity;
- robustness across contexts.

Novelty is not a criterion. Interesting metaphors are not evidence.

Prefer the smallest representational change that creates a material gain.

### 6. Solve inside the strongest frames

Only after comparing representations, reason about solutions inside the one or two strongest frames.

Highlight where conclusions differ from those produced by the original frame. This difference is the practical value of the reframing.

### 7. Define a discriminating test

Whenever possible, propose an observation, experiment, simulation, calculation, or decision outcome that would distinguish the competing frames.

Prefer tests that can invalidate a frame rather than merely produce supporting anecdotes.

## Multi-agent mode

When multiple agents, branches, or parallel workers are available, use them to search **different problem representations**, not to sample more answers inside one frame.

Read [references/multi-agent.md](references/multi-agent.md) for the full protocol.

Use multi-agent mode when:
- the framing decision is consequential;
- several plausible representations remain;
- the current frame has persistent anomalies;
- independent representation search can materially reduce correlated blind spots.

Do not use multi-agent mode merely because parallelism is available. For small questions, the single-agent workflow is usually preferable.

The minimum useful topology is:

`Frame Extractor -> parallel Representation Explorers -> Primitive Challenger -> Adversarial Critic -> Synthesis/Judge -> optional Experiment Designer`

Do not select a frame by majority vote. Similar models often produce correlated outputs. Select by explicit evidence and the criteria in **Apply selection pressure**.

If independent agents are unavailable, emulate the roles sequentially but clearly treat this as role separation rather than independent evidence.

## Iterative debate mode (optional)

The default is a single pass. Add debate rounds only when the decision is consequential and first-pass frames produced contested claims.

1. After each round, freeze an **argument map**: one line per argument with a stable id, its type (idea, claim, question, observation), the claim itself, and its typed edges (supports, contradicts, revises) to other ids.
2. In the next round, explorers receive the map and may only contribute: a rebuttal against a precise id, a revision of a precise id, or a genuinely new argument. Restating a mapped argument is rejected.
3. Stop when a round adds fewer than 3 genuinely new arguments, or after 3 rounds. If the round cap stops the debate, report "not converged" — do not present the cut-off as exhausted search.

Warning from practice: decomposition by content lens (data, code, operations, ...) inside one frame does not converge — each round finds more detail. Representation search converges better because structurally distinct frames are countable; detail is not.

## Persisting the argument graph

When a relational knowledge store is available (relknow preferred), persist the debate instead of leaving it in ephemeral context: each atomic argument becomes a note, each edge a typed relation with a note explaining why the edge exists. Use exactly one collector writer at a time — relknow guards writes with an optimistic lock (`base_hash`), so parallel writers conflict.

Persisting pays three times: rounds deduplicate against the graph instead of against transcripts, the committee reads a compact map instead of raw agent output, and the debate survives the session.

To rank complete argumentation lines by cost (the "MinSum" evaluation), the graph needs operation chains with cost vectors, not just edges. If the relknow skill is installed, read its `references/relknow-argumentation.md` for the write protocol and the `evaluate_derivations` contract before the committee phase.

## Output style

Keep the response compact unless the user asks for a full analysis.

For substantial cases, use this structure:

**Current frame** — concise reconstruction.

**Pressure points** — anomalies, hidden assumptions, or reasons the frame may be limiting.

**Alternative representation** — one to three structurally different frames.

**What remains invariant** — what every acceptable frame must still explain.

**Best current frame** — which representation currently has the strongest explanatory or decision value and why.

**Discriminating test** — what evidence would make us change our mind.

When the user is exploring interactively, do not dump the full structure at once. Advance one conceptual step at a time and challenge weak assumptions as they appear.

## Guardrails

- Do not confuse renaming concepts with changing representation.
- Do not reward complexity, jargon, or mathematical notation unless they improve explanatory or predictive power.
- Do not claim a new frame is superior solely because it is more general.
- Do not discard established successful explanations without showing how the new frame recovers them.
- Treat analogies as generators of hypotheses, not as proofs.
- Reject claims about an existing system that cite no checkable evidence (file path, measurement, document).
- State uncertainty when multiple frames remain observationally equivalent.
- In multi-agent mode, enforce representational diversity; different wording or solution tactics do not count as different frames.
- Do not treat agreement among correlated agents as independent evidence or use majority vote as the primary selector.

## Trigger examples

Typical requests include:
- "I keep analysing this but I am not getting anywhere. Am I asking the wrong question?"
- "Reframe this architecture problem."
- "What assumptions define my current search space?"
- "Can we represent this as a graph or dynamical system instead?"
- "I have two explanations that both seem plausible. What invariant or experiment separates them?"
- "Help me find the Einstein move here rather than optimizing inside the existing frame."

