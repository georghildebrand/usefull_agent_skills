# Writing style

Applies to all user-facing text: summaries after a work step, reports, tickets, PR and
commit bodies, docs, wiki pages, artifacts, and any answer longer than a few sentences. Skip it for one-line answers and short
replies; a short direct answer is already correct.

- Plain English. Readers are non-native speakers. Short sentences, common words.
- No idioms, metaphors, or figurative verbs. Say what happens literally.
  Not "trip the sandbox" but "be blocked by the sandbox". Not "blast radius" but
  "how much damage it could do". Not "earn their keep", "bit me", "belt and braces",
  "sharp edge", "steal this".
- Keep exact technical terms (symlink, hook, worktree, PATH). Do not simplify those.
- Name the concrete artifact: "the staging deploy of job 412 failed", not "the deploy
  failed". Gloss jargon and acronyms on first use. Restore the reasoning step that
  only existed in tool output, or in your own reasoning, and that the reader never saw.
- Free buried verbs: "we analysed", not "we performed an analysis of". Keep subject
  and verb close. Split nested clauses. Never a bare "This shows" - say which thing.
- Replace vague nouns (level, approach, context, process, system, framework, aspect)
  with something the reader can picture. Unpack stacked noun phrases with a
  preposition.
- No metadiscourse: "Let me", "I will now", "As mentioned above", "In summary",
  "It is worth noting that".
- Keep real uncertainty. Never restyle an unverified claim into an assertion. State
  the limit instead: "unit tests pass; integration suite not run".
- A correction stands on its own. Never point at a belief the reader cannot see.
  When you write that an assumption, hypothesis, guess, measurement or earlier claim
  was wrong, the same sentence names what it claimed and what the fact is. Not "one
  of my two assumptions was wrong" but "I assumed test_a and test_b were both
  redundant; test_b is, test_a is the only test that reaches the EMPTY branch". This
  holds even when you only ever held the belief while reasoning: the reader never saw
  it, so introduce it in the same breath as you correct it. Keeping a correction short
  means dropping the apology, not dropping what was wrong.
- Compression still applies. Plain does not mean longer.
- Don't compress an idea into an invented shorthand label the reader has not seen
  expanded before. State the actual behavior in one plain sentence on first mention;
  reuse a short label only after that. Not "kein Tag-1-Modulregister" but "we do not
  build a central module library now; we extract a module only when a second service
  needs the same pattern". Not "nie Dauer-Approver" but "the platform team never
  becomes a required approver of other teams' applies".

Leave byte-identical: identifiers, file paths, commands, error messages, log lines,
quoted text, API field names, ticket keys, and anything inside a code block.

Full rules, including the revision output contract for editing a supplied text: the
text-writer skill.
