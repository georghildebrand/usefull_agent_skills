# RFC anti-patterns

Failure modes of RFCs and design docs, with the symptom and the fix. Names in
brackets point to `sources.md`. Some patterns were described for ADRs or
architecture decisions (Zimmermann, Zhou et al.). They are applied here to
the rationale part of an RFC; that transfer is plausible but not studied.

## In the document

| Name | Symptom | Fix |
|---|---|---|
| Dishonest drawbacks or alternatives | Reviewers see the author is "disingenuous about the drawbacks or alternatives" (Rust RFC README) | Real alternatives, including "Do nothing", each with a reason. Drawbacks never empty |
| Dummy alternative (Zimmermann) | An option that cannot work is listed so the favourite looks compared | List only options that could solve the problem. If only one exists, say so and explain why |
| Sales pitch (Zimmermann) | Only upsides, marketing words, consequences left out | At least one downside per option. Evidence for each claim. Cut adjectives |
| Tunnel vision (Zimmermann) | Operations and maintenance ignored | Cross-cutting section: rollout, rollback, monitoring, security |
| Mega-document (Zimmermann; Ubl) | Drift into detail; docs over ~20 pages go unread | 1-3 pages for small work. Split above ~10 pages. Link detail out |
| Pseudo-accuracy (Zimmermann) | Scores or numbers with no basis; false urgency; the proposal does not solve the stated problem | No invented numbers. Check that the proposal answers the problem section |
| Weak motivation (Rust RFC README; paritytech skill) | No concrete problem | Concrete problem first, with "why now". If not concrete, the RFC is not ready |
| Bikeshedding (Calcado) | Review stalls on one small implementation detail | Keep implementation detail out of the RFC |
| Pasted schemas (Ubl) | Full schemas or interfaces copied in; they go stale | Link to the source. Show only the part the decision is about |
| Template padding (paritytech skill) | Every section filled, some only with filler | Leave out sections without content. "Cut every sentence that would not change a reader's mind." |
| Precedent as motivation (Rust RFC template) | "Others do it" or "it enables future work" used as the main reason | Prior art covers "both the good and the bad". Future possibilities are "not a reason to accept" |

## In the process

| Name | Symptom | Fix |
|---|---|---|
| Polished too late (Calcado; Visser) | A finished-looking doc after the code exists; reviewers go soft | Share a rough draft early. Check timing before writing |
| Diffusion of responsibility (Calcado; Visser) | "Everybody reviewed it", nobody owns it | One named decision owner. Few named approvers |
| Siloed RFC (Calcado) | Affected teams never saw it | Name affected teams. In an advice process, consult all of them |
| RFC avalanche (Calcado) | Too many RFCs; readers stop reading | RFCs only for changes beyond one team or hard to undo |
| Criticism overload (Squarespace) | Author cannot tell blockers from side remarks; unclear when work may start | Approvers answer "yes", "not yet" or "yes, if". Sort comments into blocker or remark |
| Heavy council cost (Leach) | Many hours spent on proposals that are only a little better; contested RFCs stay open for months | Low-touch review by default. One tie-breaker |
| Slow cycle (Costa) | Weeks of review with no code; decisions fixed when knowledge is lowest | Spike first. Heavy review only for one-way doors |
| No owner for follow-up | The change and its follow-up work have no owner | Name the owner of the change and of each follow-up item |

## Agent-specific

| Name | Symptom | Fix |
|---|---|---|
| Over-production and pro-skew (Zhou et al.) | Zero-shot LLMs gave 4.55 arguments per decision against 1.98 from experts, with precision about 0.27, and favoured the chosen option | Count pro and con per option. Cut arguments that change no decision |
| Verbosity (LLVM report) | "Extremely verbose, heavily formatted descriptions" that burden reviewers | Short sentences, few headings, no decoration |
| Invention | Approvers, consensus, incidents, numbers or prior discussions that are not in the inputs | Placeholders and [Assumed: ...]/[Open: ...] tags |
| Accepted by the agent | Agent sets status accepted because the user sounded sure | Status stays `draft` until a human states the outcome |
| Doc after code | RFC written after the change is merged | Label it as a record, or write an ADR or a PR description |
