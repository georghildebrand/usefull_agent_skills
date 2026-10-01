---
name: codebase-spec-reverse-engineering
description: >
  Use when performing a comprehensive reverse-engineering analysis of a codebase
  or repository to produce an exhaustive, implementation-ready Technical Specification
  Document for a clean-room reimplementation. Enforces zero-ambiguity, domain-first
  architecture, complete user flow mapping, formal algorithmic/schema definitions,
  and systematic codebase verification.
---

# Codebase Spec Reverse Engineering

Reverse-engineering an existing codebase into an exhaustive, implementation-ready **Technical Specification Document (Spec Doc)** enables a senior software engineer to re-implement the entire system from scratch in a "clean room" environment using **only** the specification document, without seeing the original source code.

---

## Core Guiding Principles

1. **Zero Ambiguity:** Avoid hand-waving statements like *"implement search logic here"* or *"handle errors appropriately"*. Specify exact data structures, algorithms, state machine transitions, regexes/grammars, database schemas, API contracts, and edge-case behaviors.
2. **Domain-First Ordering:** Clearly define domain models, invariants, theoretical constraints, and state transitions before specifying application/service boundaries and I/O logic.
3. **Clean-Room Reimplementability:** Every section must contain sufficient detail that an engineer can write functionally identical, byte-compatible, or wire-compatible code without accessing the reference codebase.
4. **Empirical Verification over Assumptions:** Never infer implementation details, variable names, or file locations without inspecting the authoritative source code using code search and file viewing.
5. **Full Subsystem Coverage:** Systematically audit all codebase layers—from low-level file locks and database DDL to template UI components, background workers, and evaluation algorithms.

---

## The 5-Phase Analysis & Generation Workflow

```
[Phase 1: Discovery & Mapping] → [Phase 2: Deep Subsystem Audit] → [Phase 3: Formal Spec Drafting] → [Phase 4: Gap & Boundary Audit] → [Phase 5: Golden Verification Criteria]
```

### Phase 1: System Discovery & Architecture Mapping
* **Build & Runtime Footprint:** Inspect package and dependency manifests (`package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `CMakeLists.txt`), build flags, compilation/linkage requirements, and target architectures.
* **Entry Points & Routing:** Locate execution entry points (`main.rs`, `index.js`, `main.go`, `app.py`), CLI command hierarchies, and HTTP/RPC route registries.
* **Documentation & ADRs:** Read `docs/`, Architectural Decision Records (ADRs), research papers, and status guides to capture the foundational **research question**, core product purpose, and architectural invariants.
* **Top-Level Inventory:** Build an exhaustive map of all packages, subdirectories, templates, and static assets.

### Phase 2: Deep Subsystem & Schema Audit
Inspect source files directly to document:
1. **Core Invariants & Limits:** Memory limits, maximum file/payload sizes, thread/concurrency primitives, process-level OS file locks (`flock`/`fcntl`), and optimistic concurrency rules (content SHA-256 hashes, ETags).
2. **Grammar & Parsers:** Multi-pass tokenizers, state machine enums, AST definitions, edge-case recovery rules, and diagnostic error codes.
3. **Persistence & Schemas:** Exact SQL DDLs (including migration histories, indices, FTS tables), journal/event-stream schemas, content-addressed storage semantics, and atomic file write algorithms (`.tmp.<pid>` → `fsync` → `rename` → `dir fsync`).
4. **Algorithmic Mechanics & Math:** Mathematical formulations (e.g. path metrics, optimization norms, scalarization formulas), graph traversal/cycle detection algorithms, and sorting invariants.
5. **Background Workers & Protocols:** Materializers, cleanup/retention planners, proposal/agent contribution envelopes, checkpointing, and bundle/pack archives.
6. **UI & User Interaction Flows:** Complete inventory of server-rendered pages, HTMX/AJAX partials, client-side JS validation rules, modal popups, and step-by-step user interaction flows.
7. **Integrations & Adapters:** AI/LLM provider abstractions, third-party read-only bridges, and fallback mechanisms.

### Phase 3: Technical Specification Document Structure

Structure the resulting `technical_specification.md` using the following standardized section template:

```markdown
# [System Name]: Technical Specification Document

**Version:** [X.Y.Z]
**Target Specification Status:** Final / Implementation-Ready
**Audience:** Senior Software Engineers (Clean-Room Implementation)
**System Type:** [System Classification]

---

## 1. System Vision & Core Invariants
### 1.1 Primary Purpose & Non-Goals
### 1.2 Core Architectural Invariants (Storage, Concurrency, Isolation, Build Rules)
### 1.3 System Capabilities & Limits Table
### 1.4 Research Question, Theoretical Framing & Multi-Agent/Committee Workflows

## 2. Domain & Data Specifications
### 2.1 Grammar, Directive Enclosure & Parser Specifications
### 2.2 Domain Taxonomy & Validation Constraints
### 2.3 Comprehensive Relational Database Schema (All DDLs & Migrations)
### 2.4 Immutable Journal / Event-Stream Database Schema

## 3. Algorithmic & Subsystem Specifications
### 3.1 Parser & Scanner State Machine Algorithms
### 3.2 Writer & Field Normalization Algorithms
### 3.3 Atomicity & Concurrency Model (Vault/File Locks, Mutexes)
### 3.4 Baseline Migration & Intake Algorithms
### 3.5 Algorithmic Mechanics (Path Mathematics, Scalarization, DAG Cycle Detection)
### 3.6 Subsystem Workers (Materializer, Retention, Checkpoints, Agent Exchange)
### 3.7 Atomic File Writer Specifications

## 4. API, Web & Interaction Specification
### 4.1 HTTP Route Inventory & Web Handler Contracts
### 4.2 CLI Command Specifications & Environment Variables
### 4.3 User Flows & UI Component Specification (Exhaustive Flow Inventory)

## 5. Integration & Adapter Contracts
### 5.1 LLM / AI Provider Abstractions & Schemas
### 5.2 External Importers & Read-Only Reference Bridges
### 5.3 Immutable File Exchange & Share Pack Specifications

## 6. Test Suite & Acceptance Criteria
### 6.1 Golden Tests & Parsing Fixtures
### 6.2 Integration & Regression Test Scenarios (Concurrency, Rebuild, Build Rules)
```

### Phase 4: Gap & Boundary Audit Checklist
Before finalizing the spec, systematically verify that:
- [ ] **No Undocumented Routes:** Every HTTP route in handlers or routers is present in the HTTP Route Table.
- [ ] **No Undocumented Schemas:** Every database table, JSON request/response schema, and block directive layout has explicit DDL/struct fields.
- [ ] **No Hand-Waved Algorithms:** Complex computations (e.g. shortest path, Pareto optimization, hashing, tokenization) include pseudo-code or formal mathematical formulas.
- [ ] **No Missing UI Flows:** Every HTML template and user interaction state (modal dialogs, autocomplete dropdowns, error banners, forms) is specified as an explicit User Flow.
- [ ] **Theoretical Question Captured:** The underlying motivation, research problem, and domain boundaries (e.g. read-only integration vs. canonical writes) are clearly stated.

### Phase 5: Golden Verification Criteria
Ensure the spec includes concrete test fixtures and acceptance criteria:
* **Golden Fixtures:** Input file text with exact expected parsed AST/error diagnostics.
* **Integration Scenarios:** Step-by-step verification procedures (e.g. optimistic concurrency failure, full index rebuild idempotency, cycle detection).
* **Build Invariants:** Static vs. dynamic linkage requirements, cross-compilation target platforms, or memory allocation constraints.

---

## Spec Review Checklist

When reviewing or self-auditing a generated Technical Specification Document:

| Check | Requirement |
|---|---|
| **Clean-Room Test** | Could an engineer build this entire system *without* seeing the original repo? |
| **No "TBD" or "TODO"** | Are all edge cases, limits, and error sentinels explicitly defined? |
| **Domain-First** | Are domain models and mathematical formulas specified before I/O & HTTP layers? |
| **UI Exhaustiveness** | Are all user interaction flows, templates, and client-side JS validations specified? |
| **State & Lock Safety** | Are process-level OS file locks, thread mutexes, and optimistic concurrency hashes fully detailed? |

