---
status: accepted
date: 2026-10-05
decision-makers: Tyler Banks
consulted: Claude (sprint 3.5)
---

# Gap mode suggests outputs of uninjected regions from their neighbours

## Context and Problem Statement

The plan's explorer has a gap mode that "highlights plausible but untested connections as research prompts" (Part 1, "Explorer"). Its example questions include a species gap: "Which BLA projections are shown in rat but untested in mouse?" Sprint 3.5 builds gap mode. Today's data holds Allen's mouse connectivity and no rat claims or homology claims (sprints 2.3 and 2.6). What counts as untested, what makes a connection plausible, and where is it computed?

## Considered Options

* Neighbours: an amygdala region no claim reports outputs for, to the targets of its neighbours (other subdivisions of the same parent)
* Species: connections shown in one species and untested in another, through homology claims
* Replication: connections seen in one experiment only (the reconciliation report's "one observation")

## Decision Outcome

Chosen option: "neighbours", built so that "species" can join later. Species gaps need rat claims and homology claims, which don't exist yet. Connections seen once are tested, so they don't belong in a mode about untested ones. The reconciliation report already counts them.

* **Untested:** an amygdala region whose outputs no claim names, in a species. That covers the region itself, its subdivisions, and any region it is part of; a claim of any result counts, absent included. No experiment is known to have injected it.
* **Plausible:** a neighbour, another subdivision of the same parent, projects to the target with a present claim (from the neighbour or one of its subdivisions). Nearby subdivisions of one structure often share targets, so a neighbour's connection is a reasonable first guess for an experiment, not more.
* **Inputs are left out.** For injections outside the amygdala, Allen's claims keep only densities of at least 0.01 (ADR 0010). There a missing claim can't tell an untested region from a tested, weak connection.
* **Computed in the build** (`build/gaps.py`), as the plan has it for graph analytics, into a `gaps` table with the database and the snapshot. Unlike routes (ADR 0026), gaps need what the page doesn't load: the atlas hierarchy, and every claim of any result. Their regions also need meshes, which the build exports.
  * Each row keeps the connections that suggest it (`suggested_by`) and the strongest density among them, and names its `basis` (`neighbours`), so species gaps can join as another basis.
* **Never evidence:** gaps are not claims. They never enter the files, the dumps (they rest on Allen claims and atlas regions, ADR 0005) or the edge counts.
* **In the brain viewer:** "Untested (gap mode)" draws the gaps dashed from each untested region. The minimum-density control applies to the suggesting density. Each row links to a connection that suggests it, and the page says these are suggestions for experiments, not evidence.

### Consequences

* Good, because each suggestion is traceable to the cited connections behind it.
* Good, because gaps shrink as data arrives: a literature claim about a region's outputs, present or absent, removes its gaps on the next build.
* Bad, because the neighbour rule is a heuristic. Subdivisions differ in their outputs, and the suggestions inherit the neighbours' strength, not the region's own.
* Bad, because Allen's coverage decides most of today's gaps. An uninjected region may already be described in papers the project hasn't extracted yet (sprint 2.3).
* Neutral: the read API and the MCP server don't serve gaps yet; the table is ready for them.
