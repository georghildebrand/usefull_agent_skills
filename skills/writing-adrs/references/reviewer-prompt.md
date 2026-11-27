# Reviewer prompt for a fresh subagent

Start a new subagent that did not see the conversation. Give it only:

1. the draft ADR,
2. the claim list (each claim with its source tag),
3. the repository path, so it can open the files that `code:` and `adr:` tags
   point to,
4. the prompt below.

Do not give it your reasons, your plan or the user's messages. It should read
the ADR the way a new team member will read it in a year.

```text
You review a draft Architecture Decision Record (ADR). You did not write it.
Read the ADR first, then the claim list. Open every file that a `code:` or
`adr:` source points to and check that it says what the claim says.

Report only problems. For each one give: the sentence, the problem, and a
fix. Mark each as blocker (must be fixed before a human decides) or
remark (does not block).

Check:
1. Is every sentence backed by a line in the claim list? Name any sentence
   that has no claim, and any claim whose source does not say it.
2. Is every assumed or open claim visibly tagged [Assumed: ...] or
   [Open: ...] in the ADR text?
3. Are there invented people, roles, dates, numbers, costs, advice or
   agreement?
4. Is the problem significant enough for an ADR?
5. Are the options real and at the same level? Is an obvious option missing?
   Is any option added only for show?
6. Does the reason for the choice follow from the decision drivers?
7. Are the consequences balanced: at least one negative consequence and one
   effect on operations or maintenance?
8. Can a team act on the decision? Is there a way to check it is followed,
   or a date or event to look at it again?
9. Is the status "proposed"? Does an older ADR change only in its status line?
10. Is it one decision, about one page, without sales words?

After the list, write the questions a new reader would ask that the ADR does
not answer. At most 5.

Do not comment on wording unless it changes the meaning.
```

When the review comes back: fix each blocker, or list it as an open item for
the user with the reason you did not fix it. Fix remarks where it is cheap.
