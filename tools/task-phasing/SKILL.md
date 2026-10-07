---
name: task-phasing
description: Decompose a large task, refactor, benchmark rebuild, migration, or research-to-implementation effort into an evidence-backed phased roadmap with an orchestrating plan, child phase docs, source-of-truth mapping, per-phase dependencies, exit criteria, validation strategy, and ready-to-use follow-up prompts. Use when the user asks to break work into milestones, phases, implementation chunks, sessions, or actionable steps across multiple turns or projects, especially when generic high-level plans would cause future guesswork.
---

# Task Phasing

Turn a broad task into a roadmap that a fresh session can execute without guessing. Prefer fewer, denser, evidence-backed phases over many generic milestones.

## Core Output

Produce:

1. one orchestrating roadmap
2. one child roadmap per phase
3. explicit source-of-truth and evidence mapping
4. clear phase ordering and dependencies
5. concrete deliverables, files, tests, risks, and exit criteria for each phase
6. one suggested prompt per phase for a fresh session

When the user only wants a lightweight decomposition, give the same structure in-message instead of writing files. Still include the evidence or assumptions behind the split.

## Non-Negotiable Standard

Do not write a roadmap until the relevant artifacts have been inspected or the missing evidence is explicitly called out. A good phase doc should answer: "What does the future agent need to read, build, verify, and avoid so it can complete this phase without rediscovering the whole project?"

Avoid roadmap-shaped placeholders. If a phase could apply to almost any project, it is too generic.

## Workflow

### 1. Build an evidence inventory

Before decomposing, inspect and summarize the real inputs:

- user request, issue, PR, design doc, paper, ticket, or product ask
- current repo or artifact state
- existing roadmaps, specs, contracts, README files, tests, fixtures, configs, and scripts
- related implementations that should be matched for comprehensiveness or style
- generated, vendored, ignored, or transitional artifacts that must not become public dependencies
- local changes already present that should not be overwritten

For each important claim in the roadmap, know which source supports it. If evidence is missing, mark it as an open question or assumption instead of burying it inside implementation work.

### 2. Map the contract before the phases

The orchestrating roadmap should include the source-of-truth contract when one exists:

- required inputs and outputs
- ownership boundaries between modules, layers, services, or packages
- public APIs, CLI contracts, schemas, data formats, or file naming conventions
- constraints from issues, specs, papers, maintainers, or benchmark verifiers
- non-goals and forbidden dependencies
- definition of done and promotion criteria

Call out mismatches between source material, current implementation, and user intent before planning implementation.

### 3. Separate discovery, decisions, and build work

Use distinct phases when the task still has open modeling, schema, UX, algorithm, data, or product-definition questions.

Typical split:

- contract, evidence, source, schema, or scaffold setup
- first runnable vertical slice
- core algorithm, engine, migration, or integration
- validation, repair, observability, fixtures, and tests
- tuning, hardening, reproduction fidelity, or rollout
- docs, cleanup, promotion, and handoff

If the problem is already fully specified, skip a standalone decision phase. Do not hide unresolved decisions inside "implementation."

### 4. Choose phase boundaries by dependency

A good phase should:

- have one clear objective
- unlock the next phase
- be testable or reviewable on its own
- have a concrete write scope or artifact scope
- avoid mixing unrelated concerns
- leave the system in a coherent state even if later phases never happen

Split phases when one part can be completed and validated without the other. Merge phases when separation would create artificial overhead.

### 5. Make each child phase a working dossier

Each child roadmap should include:

- `Goal`: one concrete outcome
- `In Scope`: specific files, modules, behaviors, commands, data, or docs to add/change
- `Out Of Scope`: adjacent work that must not creep into the phase
- `Inputs To Read`: exact source material a fresh session should inspect first
- `Implementation Notes`: constraints, algorithms, edge cases, and sequencing details
- `Validation`: focused tests, smoke commands, fixture expectations, manual checks, or metrics
- `Exit Criteria`: observable completion conditions, not intentions
- `Suggested Prompt`: a ready-to-use prompt for starting that phase later

For code projects, include likely file paths or module names when knowable. For research-to-implementation work, include paper-to-project adaptation notes and what is intentionally omitted.

### 6. Preserve validation as part of design

Do not create "testing later" plans unless the task genuinely cannot be tested earlier. Each phase should say what can be validated at that point:

- unit tests for local logic
- fixture or snapshot checks for data transformations
- CLI smoke runs for executable contracts
- contract tests for APIs and schemas
- migration dry-runs or rollback checks
- debug artifacts or metrics needed to diagnose drift

If validation depends on external systems, expensive runs, or unavailable data, say how to do a cheap local proxy and what remains for later.

### 7. Design for fresh-session handoff

Every child roadmap should let a new session start cleanly.

The suggested prompt should tell the future agent to:

- read the top-level roadmap
- read the source-of-truth spec or issue
- read the current phase doc
- inspect current implementation status and local changes
- verify mismatches before editing
- implement only that phase
- run the phase's validation checks

Avoid prompts that assume hidden memory from prior sessions.

## Orchestrating Roadmap Template

Use this structure unless the repository already has a stronger convention:

```markdown
# <Task> Roadmap

## Goal

## Source Of Truth

## Current State

## Contract And Boundaries

## Phase Order

## Cross-Phase Risks

## Overall Exit Criteria
```

Keep `Current State` and `Contract And Boundaries` factual. Do not turn them into implementation wishlists.

## Phase Doc Template

Use this structure for substantial tasks:

```markdown
# Phase N: <Name>

## Goal

## Inputs To Read

## In Scope

## Out Of Scope

## Implementation Notes

## Validation

## Exit Criteria

## Suggested Prompt
```

For small efforts, compress sections but preserve the same information.

## Calibration Checklist

Before finalizing, check:

- Does every phase cite or point to the evidence it relies on?
- Does every phase have enough detail for implementation without fresh guesswork?
- Are source-of-truth contracts and forbidden dependencies explicit?
- Are validation steps distributed across phases instead of delayed to the end?
- Are debug/observability artifacts included when score drift or behavior drift is likely?
- Are names, paths, schemas, and entrypoints concrete where the repo makes them knowable?
- Are open questions separated from build tasks?
- Are promotion or close-out criteria stricter than "docs and cleanup"?

If the answer to any item is no, harden the roadmap before presenting it.

## What To Avoid

- Do not make phases that depend on undefined inputs.
- Do not hide unresolved design questions inside an implementation phase.
- Do not create generic phases like "core implementation" without file scope, behavior scope, and validation.
- Do not create "testing later" plans when validation should shape implementation.
- Do not make every phase the same size; dependency matters more than symmetry.
- Do not write prompts that assume hidden memory from prior sessions.
- Do not optimize for shortness when the user needs durable multi-session handoff.

## Output Style

Prefer roadmap files that are concise but complete:

- one top-level roadmap
- one phase file per phase
- flat bullet lists
- concrete wording and paths
- explicit assumptions and unresolved questions

Name files predictably when writing them to disk, for example:

- `ROADMAP.md`
- `PHASE_1_<NAME>.md`
- `PHASE_2_<NAME>.md`

If the project uses a local internal-doc convention, follow that convention instead of inventing a new one.
