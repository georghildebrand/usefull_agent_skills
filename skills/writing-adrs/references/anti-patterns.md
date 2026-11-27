# ADR anti-patterns

Use this list in the self-check and give it to the reviewer subagent. Most
names come from Olaf Zimmermann (2023). The last column says how an agent
usually causes the problem.

## When writing

| Name | What you see | Fix | Typical agent cause |
|---|---|---|---|
| Fairy Tale (Wishful Thinking) | Only upsides, or statements that are always true | At least one negative consequence per option | Language models list the pros of the chosen option and leave out the cons. |
| Sales Pitch | Words such as "seamless", "best", "robust"; claims without support | Remove adjectives. Cite a source. | Generic praise from training text. |
| Free Lunch Coupon | Long-term or negative effects left out or made small | Ask for long-term costs and effects on operations | Same pro bias. |
| Dummy Alternative | A weak option added so the choice looks compared | Remove it. If there is only one option, say so and give the reason. | A template slot for "options" that the agent fills. |
| Sprint (Rush) | One option, short-term view only | Ask for a second real option and a long-term view | Missing input, not asked for. |
| Tunnel Vision | Only the local view; operations and maintenance missing | Add effects on backups, upgrades, monitoring, on-call | Agent reads code, not run books. |
| Maze | Drifts into detail that does not affect the decision | Cut to the decision and its drivers | Too much rationale: Zhou et al. (2025) counted about twice as many arguments per decision as human experts gave. |
| Blueprint in Disguise | Reads like a how-to or a rule book | Move steps to a guide. Keep the reasons. | Agent adds implementation steps. |
| Mega-ADR | Several pages, design detail inline | Link a design doc. Keep 1 to 2 pages. | Without earlier ADRs as context, model output was about twice as long (Context Matters, 2026). |
| Novel (Epic) | Several decisions in one record | One ADR per decision | Request bundles several choices. |
| Magic Tricks | Invented context, false urgency, scores without a basis | Use only sourced requirements. Remove scores. | Agent fills sections it has no input for. |
| Pseudo-alternatives | Options at different levels (a product against an approach) | Compare like with like | Options gathered from different sources. |
| Created as Accepted | New ADR has status accepted, no review happened | Status proposed | A study found about 63% of public ADRs were created as accepted. Tools such as adr-tools default to it. |

Other common problems: decisions too small for an ADR; a Context section
longer than about 10 lines; "we just picked it" as the only reason; a
reconstructed ADR without the original date or a "reconstructed" note; old
ADRs that no longer match the code.

## When reviewing

Watch for these in the reviewer's output, including your own fresh subagent:

| Name | What you see |
|---|---|
| Pass Through | Skims, gives no or only friendly comments |
| Copy Edit | Comments only on wording, not on content |
| Siding / Dead End | Takes a side in an old dispute, or blocks with no way forward |
| Self Promotion | Pushes the reviewer's own favourite option |
| Power Game | Uses rank instead of arguments |
| Groundhog Day | Raises the same point again and again |

A reviewer that only reports wording has not done the job. Ask it again for
claims without a source.
