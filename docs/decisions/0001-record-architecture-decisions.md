---
status: accepted
date: 2026-10-02
decision-makers: Tyler Banks
---

# Record architecture decisions in MADR

## Context and Problem Statement

Axonarium is maintained largely by AI agents that start every session cold. Design principle 9 ("Adopt, don't invent") and the agent operating model in [docs/plan.md](../plan.md) need design choices recorded in files that any agent or person can read, so that nothing depends on someone remembering a past conversation. How should those decisions be recorded?

## Considered Options

* MADR 4.0.0 (Markdown Architectural Decision Records)
* Michael Nygard's original ADR format
* No ADRs; decisions left in issues and pull requests

## Decision Outcome

Chosen option: "MADR 4.0.0", because it is a maintained standard with a ready template, it records the rejected options as well as the chosen one, and it lives in the repo, so every fork carries it.

Decisions live in `docs/decisions/` as `NNNN-short-title.md`, numbered in order and started from [adr-template.md](adr-template.md). An ADR is required for:

* a new dependency;
* custom code where an existing library might serve;
* replacing a building block listed in docs/plan.md, which also needs human review;
* promoting an `extra` key into the schema.

### Consequences

* Good, because decisions travel with every clone and fork, and agents can find them without access to past conversations.
* Bad, because every significant choice costs a short document.
