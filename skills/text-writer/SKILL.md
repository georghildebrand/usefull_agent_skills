---
name: text-writer
description: Use when writing or revising prose that a human will read - PR descriptions, tickets, commit bodies, README and design docs, Confluence pages, release notes, code comments, or chat answers - and when a draft reads as dense, abstract, bureaucratic, or hedged, or a reviewer says it is hard to follow.
---

# Text Writer

Prose is a user interface. The reader has a fixed working memory and no access to
what the writer knows. This skill revises drafts so the reader spends effort on
the subject, not on decoding the sentence.

Two ideas drive every rule below.

**Classic style.** Write as if showing a competent equal something in the world.
The prose is a clear window: the reader looks through it at the thing, not at the
writing. No throat-clearing, no signposting, no performance of effort.

**The curse of knowledge.** You cannot un-know the context you have. Everything
you skipped as obvious is a gap for the reader. This is the single largest source
of bad drafts, and agents have it worse than humans: an agent holds the whole
repository, the diff, and the tool output in context while the reader has a Jira
notification and forty seconds.

## When to use

* Any prose an agent produces for a human: PR body, ticket, design doc, RFC,
  incident report, wiki page, release note, commit body, docstring, chat answer.
* Revising a draft, yours or someone else's.
* A reviewer says the text is unclear, long, or vague and you need a concrete
  diagnosis rather than "tighten it up".

## When NOT to use

Do not apply this skill to text where the exact string is the content. Leave
these byte-identical:

| Never rewrite                                            | Why                                          |
| -------------------------------------------------------- | -------------------------------------------- |
| Identifiers, file paths, commands, flags                 | The reader copies them                       |
| Error messages and log lines                             | They are evidence, and they are searched for |
| Quoted user or third-party text                          | Quoting means quoting                        |
| API field names, schema keys, ticket keys, config values | They are contracts                           |
| Legal, licence, security, or compliance wording          | Precision is regulated                       |
| Code inside fenced blocks                                | Style rules do not reach into code           |

Also skip it when the user asked for a mechanical edit ("fix the typo"). Style
revision is not licence to rewrite what nobody asked about.

## The revision pass

Work through four groups in order. Order matters: closing knowledge gaps can add
words, so compress afterwards, not before.

### 1. Close the knowledge gaps

* **Gloss the jargon.** One clause, inline, no footnote. "Arabidopsis, a flowering
  mustard plant". "the DAB, the Databricks Asset Bundle that defines how the job is deployed".
* **Restore the skipped step.** Reconstruct the reasoning you treated as obvious.
  Agents skip the step that came from a tool call the reader never saw.
* **Drop nerdview.** Internal or process-facing terms the reader does not share:
  say what changed for them, not what your pipeline calls it.
* **Name the concrete artifact.** "the deploy failed" → "the staging deploy of
  job 412 failed". Vagueness here is almost always curse of knowledge, not brevity.

### 2. Fix sentence mechanics

* **Keep subject and verb close.** Every word between them is held in working
  memory at cost.
* **Unnest.** Break centre-embedded clauses into separate sentences. A clause
  inside a clause inside a clause is a stack overflow for the reader.
* **Free the buried verb.** Turn nominalisations back into verbs: "we performed an
  analysis of" → "we analysed"; "the implementation of a fix" → "we fixed".
* **Prefer the active voice.** Use the passive deliberately, when the actor is
  unknown or irrelevant, or when the object is the topic of the paragraph.
* **No bare demonstratives.** Not "This shows" but "This regression shows". A bare
  "this" forces the reader to re-scan the previous sentence.

### 3. Drain the noun phrases

The five contributors to heavy noun phrases (DeScioli & Pinker, 2021):

| Plague               | Symptom                                                                               | Fix                                                                                                                |
| -------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Piled modifiers      | `noun noun noun`, `adjective adjective noun`                                          | Unpack with a preposition or relative clause: "precinct-level electoral returns" → "electoral returns by precinct" |
| Needless words       | The modifier is already implied by the noun                                           | "local economic conditions" → "the local economy"                                                                  |
| Nebulous nouns       | *level, approach, context, perspective, process, system, variable, framework, aspect* | Replace with something the reader can picture                                                                      |
| Missing prepositions | Two nouns collide and the relation is guessed                                         | Insert the preposition that states the relation                                                                    |
| Buried verbs         | The action hides inside a noun                                                        | See group 2                                                                                                        |

### 4. Cut the scaffolding

* **No metadiscourse.** Delete "In this section we will", "As mentioned above",
  "It is worth noting that", "Let me", "I will now". Let structure carry structure.
* **No abbreviations you invented.** A short real name beats an acronym the reader
  must decode.
* **No filler hedges** — "somewhat", "relatively", "arguably", "I would suggest",
  "it seems that" — when nothing is actually uncertain.

**Guard rail on hedges, specific to agents.** Distinguish filler hedging from real
epistemic state. If you did not verify something, the hedge is the content and it
stays. Never let a style pass turn "the tests probably pass, I did not run the
integration suite" into "the tests pass". Replace the vague hedge with the precise
limit instead: "unit tests pass; integration suite not run".

## Output contract

Never return the revised text alone in a bare wall of prose. Return exactly three
parts, in this order:

1. **Diagnosis** — at most three bullets naming which problems dominate, using the
   names above (buried verbs, nebulous nouns, centre-embedding). Named problems
   are learnable; "it was unclear" is not.
2. **Revised text** — the complete text, ready to paste. Not a diff, not excerpts.
3. **Two before/after pairs** — one sentence each, showing the mechanism that was
   removed. Two, not ten.

When the revision would change meaning, do not guess. Revise everything else, and
list the meaning-level questions under a fourth heading, **Open questions**.

## Language notes

The rules are language-independent; the surface cues are not.

**German.** Nominalisations end in *-ung, -heit, -keit, -ation, -ismus*. Verb-final
subordinate clauses stretch the subject-verb distance by design, so unnesting
matters more than in English. Cut filler relative pronouns (*welcher/welche/welches*).
Compound nouns are the local form of piled modifiers.

**English.** Watch `-tion`, `-ment`, `-ance` nominalisations, stacked noun adjuncts,
and the filler `which`.

## Common mistakes

| Mistake                                                       | Fix                                                        |
| ------------------------------------------------------------- | ---------------------------------------------------------- |
| Rewriting for style and silently changing a claim             | Meaning is frozen. Unclear meaning goes to Open questions. |
| Stripping a real hedge and asserting an unverified fact       | Verified facts assert. Unverified ones state their limit.  |
| Editing identifiers, paths, or error strings inside prose     | They are quoted content. Leave them.                       |
| Producing a shorter text that is now missing the jargon gloss | Group 1 runs before group 4, and it may add words.         |
| Applying the pass to a one-line answer                        | A short direct answer is already classic style.            |
| Adding "In summary" to a three-paragraph text                 | That is metadiscourse.                                     |

## Attribution

The framework is **Steven Pinker, *The Sense of Style: The Thinking Person's Guide
to Writing in the 21st Century*** (Viking, 2014) — classic style, the curse of
knowledge, and the cognitive account of why syntax that overloads working memory
feels like bad writing. Pinker is a cognitive psychologist and linguist at Harvard,
and he takes the descriptive rather than prescriptive line: a rule earns its place
by making the reader's job easier, not by tradition.

Classic style itself comes from **Francis-Noël Thomas & Mark Turner, *Clear and
Simple as the Truth*** (Princeton, 1994), which Pinker builds on.

The five plagues in group 3 are not from the book. They come from **Peter DeScioli
& Steven Pinker, "Piled Modifiers, Buried Verbs, and Other Turgid Prose in the
American Political Science Review", *PS: Political Science & Politics* 55(1), 2021**
— an empirical audit of one journal issue that documented over a thousand examples
and grouped them into these five contributors to heavy noun phrases.