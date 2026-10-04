---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint 1.6)
---

# The reconciliation report: computed by the build, published with CI's runs

## Context and Problem Statement

Sprint 1.6 asks for a report of "agreement, conflict and silence between sources, as a figure in the repo". The plan's Reconciler flags contradictions and gaps and never resolves them, and cross-source agreement is to be reported per release. Two things changed the sprint's shape. BAMS is blocked on permission (ADR 0005), and SCKAN moved to Phase 7a (maintainer, 4 October 2026), so for now the sources are the Allen Mouse Brain Connectivity Atlas, made at build time, and whatever the literature adds. And the Allen claims may not be committed (ADR 0005), so neither may a report computed from them. Where is the report computed, and where does it live?

## Considered Options

* Computed by the build from every claim (committed and build-time); published in CI's run summary and as a run artifact
* Committed to the repository after each change
* A page on the site

## Decision Outcome

Chosen option: "computed by the build, published with CI's runs", because the build already holds every claim, including the Allen claims that never reach the repository, and CI already rebuilds everything on every pull request and merge.

* **What it reports** (`build/reconcile.py`, `python -m build --report DIR`):
  * every connection's agreement: sources agreeing, one source contradicting another (one found it, one tested it and didn't), one source replicated across experiments or figures, or a single observation;
  * the same split for the amygdala's outputs and inputs;
  * every conflict, listed with each side's result, never resolved;
  * how many outputs and inputs remain at projection density thresholds from 0.01 to 0.2, and how many in two or more experiments. This is the evidence for ADR 0010's open question: whether low-density inputs, which may be fibres of passage, need a higher threshold or should stay proposed;
  * silence: the amygdala regions and subdivisions no claim names, and those with no outputs or inputs measured.

  A source is a cited paper or dataset; claims are grouped by how they came in (an ingester's adapter, or the literature). Retracted claims are left out.
* **Files:** `reconciliation.json` (the numbers), `reconciliation.md` (the tables) and `reconciliation.svg` (the figure, with matplotlib), reproducible byte for byte from the same claims.
* **Where it lives:** CI's `checks` job writes it on every pull request and push to `main`, appends the Markdown to the run's summary, and keeps all three files as the `reconciliation` artifact for 30 days. A pull request's run therefore shows how it changes agreement. Nothing is committed, and releases leave it out, like all Allen-derived content (ADR 0005).
* **Dependency:** matplotlib 3.11.2 in the `build` group, the standard Python plotting library, for the figure.

### Consequences

* Good, because the report always matches the data on its commit, and reviewers see it without running anything.
* Good, because literature claims from sprint 2.3 join the comparison with no change: each paper is a source.
* Bad, because "a figure in the repo" became "a figure with every CI run": the figure holds Allen-derived numbers. Once the Allen Institute grants permission, the report can be committed or put on the site.
* Bad, because "tested and not found" is only known from claims with `result: absent`. Allen's below-threshold targets aren't claims (ADR 0010), so the report can't yet say an Allen experiment contradicts a literature claim of a connection.
* Neutral: matplotlib adds about 10 MB to the build environment.
