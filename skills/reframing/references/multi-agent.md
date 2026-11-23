# Multi-Agent Reframing

Use this protocol when multiple agents or parallel reasoning branches are available and the problem is important enough to justify representation search.

## Goal

Create epistemic diversity, not answer diversity. Parallel agents must search different representations of the problem rather than independently optimizing the same framing.

## Roles

### Frame Extractor
Reconstruct the current frame only. Identify primitives, relations, assumptions, objective, observations, and invariants. Do not solve the problem.

### Representation Explorers
Assign each explorer a distinct representational family or an explicit instruction to invent a structurally different one. Each explorer must state:
- changed primitives or relations;
- preserved invariants;
- anomaly better explained;
- prediction or decision that differs from the original frame.

Reject outputs that merely rename concepts.

### Primitive Challenger
Do not solve or reframe directly. Challenge the primitives shared by the other agents. Ask which entities, boundaries, variables, objectives, or invariants were assumed rather than demonstrated.

### Adversarial Critic
Attempt to falsify each candidate frame. Look for lost invariants, hidden assumptions, circular explanations, untestable claims, and complexity disguised as sophistication.

### Collector (optional, required for debate rounds)
Persist arguments into the knowledge graph after each round: atomic notes, typed edges, deduplicated against the existing graph. Exactly one collector writes at a time. Returns the frozen argument map for the next round. If the relknow skill is installed, see its `references/relknow-argumentation.md` for the write protocol.

### Synthesis/Judge
Compare surviving frames using the same criteria: explanatory power, assumptions, anomaly coverage, testability, decision relevance, and complexity. Do not use majority vote. Correlated agreement among similar agents is weak evidence. When the argument graph carries operation chains with cost vectors, rank complete argumentation lines with `evaluate_derivations` (linear = MinSum, tchebyscheff = robust) under at least two profiles and report profile disagreement instead of averaging it away.

### Experiment Designer
When more than one frame survives, propose the cheapest discriminating test: observation, simulation, calculation, prototype, or decision outcome that would separate them.

## Diversity contract

Parallel branches must differ in at least one of:
- primitives;
- relation structure;
- abstraction level;
- objective function;
- causal assumptions;
- state representation;
- invariants treated as fundamental.

Different wording, examples, or solution tactics do not count as different frames.

## Orchestration

Use this sequence:

1. Run one Frame Extractor.
2. Freeze the observations and required invariants as shared input.
3. Run 3-5 Representation Explorers independently. Do not expose their candidate frames to one another before first-pass generation.
4. Run the Primitive Challenger across all candidates.
5. Run the Adversarial Critic on the reduced set.
6. Run the Synthesis/Judge without majority voting.
7. If ambiguity remains, run the Experiment Designer.
8. Solve only inside the strongest one or two surviving frames.

For small personal questions, use fewer branches. Prefer three genuinely different frames over ten correlated ones.

## Debate rounds (optional extension)

For consequential decisions with contested first-pass claims, insert rounds between steps 3 and 4:

1. Collector freezes the argument map (id, type, claim, typed edges per argument).
2. Explorers re-run against the map. Allowed contributions: rebuttal against a precise id, revision of a precise id, genuinely new argument. Restatements are rejected and do not count as new.
3. Stop when a round adds fewer than 3 genuinely new arguments, or after 3 rounds. A cap-stop must be reported as "not converged".

Content-lens decomposition (data, code, operations, ...) inside one frame does not converge by itself; enforce the diversity contract even across rounds.

## Fallback without subagents

If the runtime cannot spawn independent agents, simulate the protocol sequentially while enforcing isolation:
- write the shared observations and invariants first;
- generate each candidate under an explicit diversity constraint;
- do not let later candidates merely refine earlier ones;
- perform criticism only after candidate generation is complete.

State that this is sequential role separation, not independent multi-agent evidence.
