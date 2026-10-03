---
status: accepted
date: 2026-10-02
decision-makers: Tyler Banks
---

# Apache-2.0 for code, CC BY 4.0 for data

## Context and Problem Statement

The plan left the code licence open: MIT or Apache-2.0. Project-curated data was already set to CC BY 4.0. Data ingested from other sources comes under varied licences; for example, the Allen Brain Cell Atlas releases its 10x single-cell data under CC BY-NC 4.0. Which licence should the code use, and how should mixed licences be kept straight?

## Considered Options

* Apache-2.0
* MIT

## Decision Outcome

Chosen option: "Apache-2.0", because it includes an explicit patent grant from every contributor, which universities and a future institutional home usually prefer.

* Code, docs and everything else not listed below: Apache-2.0.
* Project-curated data: CC BY 4.0.
* Ingested data keeps its upstream licence, declared per path in [REUSE.toml](../../REUSE.toml). Non-commercial data is linked, not copied.
* One copied text keeps its own licence: the MADR template (CC0 1.0).
* `reuse lint` in CI fails if any file lacks a declared licence.

### Consequences

* Good, because contributors grant patent rights explicitly, and every file's licence can be checked by machine.
* Bad, because Apache-2.0 is incompatible with GPLv2-only code. This is accepted.
* Bad, because every adapter that copies data must add a REUSE annotation. Sprint 1.1 records each source's terms.
