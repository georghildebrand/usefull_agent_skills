---
name: c4-architecture-diagrams
description: >
  Use when creating, reviewing, or restructuring C4 architecture diagrams
  (System Context / Container / Component) as PlantUML source in a
  diagrams-as-code repository. Covers which level an element belongs to, the
  classification rules for the hard cases (managed cloud services, message
  buses, microservices, SPAs, libraries), a shared conventions include, status
  tags for architecture that is not built yet, the edit-compile-commit loop,
  and a review checklist. Not for UML class diagrams, sequence-only diagrams,
  or one-off sketches.
---

# C4 Architecture Diagrams as Code

C4 describes the **static structure** of a software system at four zoom levels.
Each level answers one question for one audience. The value comes from *not*
mixing them.

| Level | Scope | Primary elements | Audience |
|---|---|---|---|
| L1 System Context | one software system | the system, plus the people and external systems it talks to | everybody, technical and non-technical |
| L2 Container | one software system | containers inside it | technical people inside and outside the team |
| L3 Component | one container | components inside that container | the team that owns the container |
| L4 Code | one component | classes, interfaces, functions | architects/developers — but see below |

Use only the levels that add value. Most teams get most of the value from L1
and L2. **Do not hand-draw L4** — the official recommendation is either to not
create it at all or to generate it on demand from the IDE.

C4 covers static structure only. Business processes, workflows, state machines,
domain models and data models are **out of scope by design** — supplement with
other notations rather than bending C4 to cover them.

## Supplementary Views

These are not extra levels. They sit alongside the four.

| View | Scope | What it shows |
|---|---|---|
| System Landscape | an enterprise | many systems together; a System Context without one system in focus |
| Dynamic | enterprise, system, or container | how existing elements collaborate at runtime, with **numbered** interactions |
| Deployment | one software system | containers mapped onto deployment nodes (physical, VM, container, execution environment); nodes can nest |
| Interfaces/contracts | a boundary | schemas, auth flows, API and tool catalogs |

A Container diagram deliberately says nothing about deployment, clustering,
replication or failover. That is what the deployment view is for.

## When to Use

- Adding or changing a diagram in an architecture-as-code repository.
- Reviewing a diagram someone else wrote.
- Deciding where a new element belongs, or whether one diagram should split.
- Setting up a new architecture repository.

## Repository Layout

Organize by **audience**, not by org chart. A layout that has held up:

```
architecture/
├── includes/         # conventions.puml — included by every diagram
├── platform/         # L1 + L2 — the whole system, cross-team
├── products/<name>/  # L3 — one directory per container/repo, team-internal
├── interfaces/       # contracts: schemas, auth flows, tool/API catalogs
├── deployment/       # infrastructure topology, CI/CD pipelines
└── security/         # identity flows, trust boundaries, policy model
```

Rules that make this work:

- **One `.puml` per diagram**, named for its level:
  `C4_Level1_Context.puml`, `C4_Level2_Container.puml`,
  `C4_Level3_Component.puml`.
- **Commit both the `.puml` source and the rendered `.svg`.** Reviewers and
  wiki embeds read the SVG; the source is what you diff. SVG over PNG — it is
  text, so the diff is reviewable, and it stays sharp when zoomed. Plain-text
  diagram source is also what gives you version history, comparison between
  versions, and the ability to revert.
- **Each directory gets a `README.md`** saying what the diagrams there mean and
  what is still open. Diagrams carry structure, prose carries reasoning.
- **L3 lives next to the product it describes** so it is obvious which diagram
  goes stale when that code changes.

## Classification: the Hard Cases

Most bad C4 diagrams are level confusion, not ugly layout. A container is
"something that must be running for the system to work" — a separately
deployable/runnable process space or data store. A component is a grouping of
related functionality behind a well-defined interface, living **inside** one
container, in the same process space.

Work through these in order; they resolve almost every real argument.

**Managed cloud data services (object storage, managed relational databases,
CDNs) → container.** You do not run the service, but you own the buckets and
the schemas, and they are an integral part of your architecture. Do not push
them out to an external system just because they are hosted elsewhere.

**Microservices and serverless functions → depends on ownership.** Owned by
another team and outside your control → external software system, drawn closed.
Owned by you → container, alongside the data stores it uses. A microservice is
just a container with fewer components in it.

**Web application: one container or two.** A server-side app that mostly serves
static HTML is **one** container. If it also delivers a significant JavaScript
application that runs in the browser, that is **two** containers — they are two
process spaces communicating over an inter-process mechanism, and each can be
zoomed into separately.

**JAR / assembly / DLL / module / package / namespace / folder → usually
neither.** A container is a runtime construct; these organize code inside it.
They are usually not components either: components partition *functionality* at
runtime, not source-tree structure. A one-to-one mapping sometimes exists (one
assembly per component in a hexagonal architecture), but do not assume it.

**Shared library or framework → not a container.** Draw it as a component in
each container that uses it, or use colour to mark which parts of the system are
bespoke versus provided.

**External systems stay closed.** If you do not own it and cannot change it,
draw only its boundary. Never open up an external system's internals — you are
guessing, and the guess ages badly.

**Message bus, API gateway, service mesh → decide deliberately, there are two
valid options.**

- *Show the intermediary*: A sends a message to the bus, the bus forwards it to
  B. Accurate, but the hub-and-spoke shape hides the fact that producer and
  consumer are coupled to each other.
- *Omit the intermediary*: draw A → B directly, and use a line style, colour or
  text label to say the interaction goes via an intermediary. This usually tells
  the clearer story, and is the option the C4 author leans toward.

A third variant appears in some C4 guidance: model the individual topics or
queues as separate elements. That surfaces pub/sub fan-out well, but it inflates
the box count fast. Pick one approach per repository and put it in the
conventions file — the failure mode here is three diagrams in one repo each
doing it differently.

**Box-count test.** Aim for 5–15 elements. Past roughly 20 elements plus their
relationships, a diagram becomes cluttered very quickly and the cognitive load
stops it being read at all. Split by business area, functional grouping, bounded
context, use case or feature set — but keep every split diagram at the **same
level of abstraction**, each telling a different part of the same story.

## PlantUML Mechanics

### Include exactly one C4 source

Pick one and never mix them in the same file:

```plantuml
!include <C4/C4_Container>   ' PlantUML stdlib: offline, pinned to the PlantUML release
```

```plantuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml
' remote master: always latest, needs network on every render, unpinned
```

**Prefer the stdlib form.** It renders offline, in CI, and behind a proxy, and
the version moves only when you bump PlantUML. Including both in one file
double-defines the macros — it may still render, but which definition wins is
undefined. If you need a feature not yet in the stdlib, use the remote form
with a **release tag** in the URL, not `master`, and use it alone.

### One shared conventions file

Every diagram includes the same `includes/conventions.puml`. It is the single
source of truth for rendering settings, tags, and links:

```plantuml
' architecture/includes/conventions.puml

' ---------- rendering ----------
skinparam dpi 300
skinparam wrapWidth 300
skinparam maxMessageSize 150

' ---------- lifecycle status tags ----------
AddElementTag("todo",    $bgColor="#FFF2CC", $fontColor="#D6B656", $borderColor="#D6B656")
AddElementTag("doing",   $bgColor="#E0FFD1", $fontColor="#32CD32", $borderColor="#32CD32")
AddElementTag("skipped", $bgColor="#F0F0F0", $fontColor="#888888", $borderColor="#CCCCCC")
' "done" is the default C4 style — no tag needed

' ---------- semantic tags ----------
AddElementTag("security-sensitive", $bgColor="#F8D7DA", $fontColor="#842029", $borderColor="#DC3545")
AddRelTag("auth_flow",  $textColor="#842029", $lineColor="#DC3545", $lineStyle=DashedLine())
AddRelTag("data_flow",  $textColor="blue",    $lineColor="blue",    $lineThickness=2)

' ---------- repo registry: one constant per repo, used for click-through links ----------
!define REPO_SERVICE_A_URL "https://<host>/<org>/<service-a>"
```

Include it with a relative path — `../includes/conventions.puml` from a
top-level directory, `../../includes/conventions.puml` from `products/<name>/`.
Every colour, shape and line style used anywhere in the repo is defined here and
nowhere else. That is what keeps a diagram drawn by one person readable to
someone who only ever read a diagram drawn by another.

### Status tags: draw the plan without lying

An architecture repo describes a system that is partly built. Colour is how you
keep "exists" and "planned" apart:

```plantuml
Container(svc, "Ingestion Service", "Python, FastAPI", "Live since <date>.")
Container(cache, "Result Cache", "Redis", "Not built yet.") <<todo>>
Container(old, "Legacy Exporter", "Java", "Replaced by <x>; kept for rollback.") <<skipped>>
```

Two rules that prevent the most damaging failure of an architecture repo:

- **Never draw an open decision as settled.** If option A vs option B is still
  open, either draw both tagged `<<todo>>`, or draw neither and say so in the
  README. A diagram is read as a commitment.
- **Put a status note on any diagram whose subject is not fully built**, with a
  date and a pointer to the ticket or decision record that will resolve it.

### Titles, labels, legend

```plantuml
@startuml
!include <C4/C4_Container>
!include ../includes/conventions.puml

!define LAYOUT_WITH_LEGEND
top to bottom direction

title Container diagram for <System Name>

Person(user, "Analyst", "Runs forecasts from the web UI")
System_Ext(idp, "Identity Provider", "The customer's own tenant IdP")

System_Boundary(sys, "<System Name>") {
  Container(api,  "API", "Python, FastAPI", "Accepts and validates run requests")
  ContainerDb(db, "Result Store", "PostgreSQL", "Stores runs and forecast outputs")
}

Rel(user, api, "Submits a forecast run", "HTTPS")
Rel(api, idp,  "Validates the caller's token", "OIDC")
Rel(api, db,   "Reads and writes run records", "SQL/TLS")

SHOW_LEGEND()
@enduml
```

**Diagrams**
- A `title` stating the **diagram type and scope** — "Container diagram for X",
  not "Architecture".
- A key/legend explaining every shape, colour, border style, line type and
  arrow head used. If you follow a standard notation, naming that notation in
  the legend is enough.
- Acronyms and abbreviations either understandable to the whole audience, or
  expanded in the legend.

**Elements**
- The type of every element explicitly specified — Person, Software System,
  Container, Component. Stripping the type introduces ambiguity.
- A short description on every element, giving an at-a-glance view of its
  responsibilities. Do not remove it "for simplicity"; make a separate
  cut-down diagram if an exec deck needs one.
- A technology explicitly specified on **every container and component**.
- Specific names. "Business Logic" and "Integration Layer" carry no
  information — name what it actually does.

**Relationships**
- Every line represents **one** unidirectional relationship. Two directions
  means two lines.
- Every line labelled, with the label consistent with the arrow direction and
  stating intent. Be specific: "Sends customer update events to" beats
  "customer update events", and both beat "Uses".
- Lines between containers represent inter-process communication — label the
  technology or protocol.
- Whether lines mean dependency or data flow is your choice, but be consistent
  and make the description match the arrow direction.
- No isolated elements. A box with no relationship is a sign the diagram is
  incomplete.

Link a container or component to its repository so readers can jump to the
code: `Container(...) [[REPO_SERVICE_A_URL{Open Repository}]]`.

**A note on conflicting advice.** General diagramming guidance sometimes says to
keep technology choices off architecture diagrams and put them in the prose
instead. C4 requires the opposite: technology on every container and component
is one of its core notation rules, because a Container diagram whose purpose is
to show the high-level technology choices cannot do that without them. Inside a
C4 repository, follow C4.

## Diagramming vs Modelling

This skill describes **diagramming**: separate diagrams, each maintained by
hand, in a tool that understands boxes and lines but not semantics. That is the
right default and the barrier to entry is low.

It has a known ceiling. You cannot ask a set of diagrams "what depends on
component X?", and elements shared across diagrams are kept in sync by hand.
When the real question you keep asking is a dependency question rather than a
communication question — especially at L3, where large systems produce
component diagrams that are hard to keep current and that few people read — the
answer is not more diagrams. It is a **model**: one definition of all elements
and relationships, with diagrams and other visualisations generated as views on
top of it. Dedicated C4 modelling tools exist for this.

Signals that you have outgrown diagramming: L3 diagrams that nobody opens,
repeated manual renaming of the same element in five files, or a recurring
"what breaks if we change X" question that no diagram answers.

## How Fast Each Level Rots

Plan maintenance around this rather than treating all diagrams alike.

| Level | Change rate | Consequence |
|---|---|---|
| L1 Context | very slow | write once, revisit per quarter |
| L2 Container | slow — faster with many microservices/functions | review when a container is added or removed |
| L3 Component | fast under active development | keep coarse, or generate; review on significant change to that container |
| L4 Code | outdated almost immediately | do not hand-maintain |

Two practical consequences. First, put "diagram updated" in the definition of
done for any change that alters structure — otherwise it never happens. Second,
blend generated and hand-drawn: generate what tooling can render cleanly, and
hand-draw what source code cannot express, such as deployment topology or how a
quality attribute is met.

## Workflow

```bash
# 1. edit the .puml in the directory matching its level
# 2. render locally
make compile          # changed .puml files only
make compile-all      # everything, after touching conventions.puml
# 3. stage source AND rendering
git add architecture/<dir>/<diagram>.puml architecture/<dir>/<diagram>.svg
# 4. record the change in CHANGELOG.md, referencing the ticket
# 5. commit and open a PR
```

Notes on the build:

- Changed-only compilation must skip include/partial files (no `@startuml`) —
  they are not renderable on their own. **After editing `conventions.puml`, run
  `compile-all`**, otherwise the committed SVGs drift from the source.
- Set `PLANTUML_LIMIT_SIZE` (e.g. `32000`) before rendering, or large diagrams
  are silently truncated.
- Delete generated `.cmapx` files; they are build artefacts, not source.
- CI can render changed `.puml` on PR and commit SVGs back. That is a
  convenience, not a substitute — render locally so you review your own output
  before anyone else does.
- Version the repo with Keep a Changelog + SemVer: MAJOR = architectural
  redesign, MINOR = new diagrams, PATCH = corrections.

## Review Checklist

The single question behind all of it: **can this diagram stand alone and be
understood without someone narrating it?** If it raises more questions than it
answers, it is not finished.

**Diagram**
- [ ] Title states the diagram type and the scope.
- [ ] Has a legend, and every colour/shape/line style/arrow head used appears in it.
- [ ] Sits in the directory that matches its level and audience.
- [ ] 5–15 elements; never past ~20.
- [ ] One level of abstraction only — no code elements on a container diagram,
      no database tables next to business systems.
- [ ] Static and runtime elements not mixed in one diagram.

**Elements**
- [ ] Every element has a name, an explicit type, a description, and — for
      containers and components — a technology.
- [ ] Names are specific, not "business logic" or "integration layer".
- [ ] Containers are deployable; components are not. No mixing.
- [ ] Managed data services you own the contents of are containers, not
      external systems.
- [ ] External systems are closed boxes — no internals shown.
- [ ] Every acronym is either universally known or expanded.
- [ ] Anything not yet built carries a status tag, not the default style.
- [ ] No isolated element without a relationship.

**Relationships**
- [ ] Every line is unidirectional and labelled.
- [ ] The label states intent and reads correctly in the arrow's direction.
- [ ] No single-word labels like "Uses".
- [ ] Inter-container lines state the protocol.

**Consistency**
- [ ] Includes `conventions.puml`; defines no local colours or skinparams.
- [ ] Includes exactly one C4 macro source.
- [ ] Every container on L2 that has an L3 diagram is named identically in both.
- [ ] Nothing depends on verbal explanation. If it was said out loud and matters,
      it is on the diagram or in the README.
- [ ] The rendered SVG in the commit matches the `.puml` source.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Shared library as a container | Not deployable; implies a running process | Component inside each consuming container |
| Managed object store / DB drawn as external system | You own the buckets and schemas; it is part of your architecture | Container |
| Inventing a "subsystem" or "module" level | Undefined abstraction; readers cannot tell what it is | Use the defined levels; split into more diagrams |
| Rationale and rejected options on the diagram | Diagrams show outcome, not deliberation | ADR or decision record, linked from the README |
| Runtime elements mixed with static ones | Two categories, one picture | Deployment or dynamic view |
| Text stripped from boxes to look clean | Ambiguity costs more than density | Keep descriptions; make a cut-down variant for the exec deck |
| Element type left off | Reader cannot tell a container from a system | State the type explicitly |
| Bidirectional arrow | Hides which side initiates | Two labelled lines |
| "I will explain this part verbally" | Whatever is not on the diagram is lost to the next reader | Put it on the diagram or in the README |
| Colours with no legend entry | Reader assumes meaning that is not there | Legend, or drop the colour |
| One diagram per quality attribute, each incomplete | Fragmentation; nothing is the source of truth | Merge them, or delete the ones not tied to a real requirement |
| No deployment view anywhere | Where it runs and how it ships is invisible | Add a deployment diagram |
| Diagram edited, SVG not re-rendered | Everyone reads the stale rendering | Render before commit; treat drift as a broken build |
| Open decision drawn as the target state | Readers implement it | Tag both options `<<todo>>`, or draw neither and say so |

## Two Misconceptions Worth Correcting Out Loud

- **C4 levels are not a process or a team structure.** The business analyst does
  not own L1 while developers own L3. C4 describes a system at different
  abstraction levels and implies nothing about how software gets delivered.
- **The terminology is not fixed.** If "container" collides with Docker in your
  team's head, or "component" and "class" do not map to your language, rename
  them. The only requirement is that everybody explicitly understands the terms
  you chose. Write them in the conventions file.

If your team documents with arc42, C4 maps onto it: Context and Scope → System
Context; Building Block View level 1 → Container; level 2 → Component; level 3 →
Code.

## Blind Spots to Flag

Raise these when they apply — the failures a checklist will not catch.

- **No owner per diagram.** A diagram nobody owns is stale within a quarter.
  Name an owner in the directory README.
- **No staleness signal.** Nothing tells a reader whether a diagram is current.
  Date the status note, or compare the diagram's last-changed date against the
  described code's.
- **Under- and over-documenting are both real.** Too few diagrams and parts of
  the architecture are undocumented; too many and the effort to keep them
  consistent swamps the benefit. Pick the number that answers actual stakeholder
  questions, and say no to the rest.
- **The repo describes intent, not reality.** If most boxes are `<<todo>>`, say
  so at the top of the README. Otherwise the repo reads as a system that exists.

## Sources

- [c4model.com](https://c4model.com/) — Simon Brown. Abstractions, per-level
  scope and audience, notation rules, metamodel, FAQ (the classification cases
  above), diagramming vs modelling.
- [Misuses and Mistakes of the C4 model](https://www.workingsoftware.dev/misuses-and-mistakes-of-the-c4-model/)
- [The Art of Crafting Architectural Diagrams](https://www.infoq.com/articles/crafting-architectural-diagrams/)
  — Ionut Balosin, InfoQ. General diagramming pitfalls, legend and consistency
  guidance, keeping diagrams current. Note its advice to keep technology off
  diagrams conflicts with C4; inside a C4 repo, follow C4.
- [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML)
