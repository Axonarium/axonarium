---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# Allen mouse connectivity: build-time region-level claims

## Context and Problem Statement

The Allen Mouse Brain Connectivity Atlas (Oh et al. 2014) is the main v1 source of mouse region-level connectivity (plan, Part 2). Its terms allow research and non-commercial use but not commercial redistribution, while project data is CC BY 4.0; until the Allen Institute grants permission, Allen-derived content is read at build time and never committed (ADR 0005). How does the project turn Allen experiments into claims?

## Considered Options

* Build-time claims from the Allen REST API, checked like committed claims
* AllenSDK's `MouseConnectivityCache`
* Waiting for permission and committing claims

## Decision Outcome

Chosen option: "build-time claims from the REST API", because it puts real amygdala connectivity on the live site now, within ADR 0005, and AllenSDK can't be used.

* **Access:** the Allen Brain Map REST API (RMA queries) through `requests` with urllib3 `Retry`. AllenSDK 2.16.2, the dedicated package, can't install on Python 3.13: it pins numpy < 1.24 and pandas 1.5.3.
* **Experiments:** Mouse Connectivity Projection experiments (product 5) that passed QC, from wild-type mice with a single injection whose primary structure is in the pinned atlas, read a page at a time in ID order. Outputs come from the 22 with the primary injection in an amygdala region or its subdivisions (sprint 1.2's amygdala regions, from UBERON); inputs from the 153 others that label an amygdala summary structure (3 October 2026). Cre-line experiments label cell types and wait for neuron-type claims.
* **Claims:** one per experiment and target among Allen's 316 summary structures (excluding the injection structure, and the few the pinned atlas lacks) with projection density (both hemispheres) of at least 0.01; for inputs, only the amygdala's summary structures are targets. Each is `projects_to`, anterograde tracer, present, sign unknown, with the projection density as a measurement, citing Oh et al. 2014 (DOI 10.1038/nature13186, whose source record is committed) with the experiment as the locator.
* **Spill-over:** Allen's primary injection structure often holds only 30 to 55 % of the injected volume. Targets that themselves received tracer are never claims (they are labelled at the injection site), each claim states the primary structure's share of the injection (its injected volume over the whole injection's, Allen's root structure, so fibre tracts count as off-target), and claims from experiments with less than half of it in the primary structure are `proposed`, not `accepted`. On 3 October 2026: 1,276 output claims (363 accepted) and 777 input claims (354 accepted), 1,039 connections.
* **Provenance:** curated by an agent with role `ingester`; for an agent with no language model, `model` is `deterministic-adapter` and `prompt` is the adapter's versioned procedure (`allen-connectivity@1.2.0`), bumped whenever its output changes.
* **Idempotence:** claim IDs are a hash of the experiment and target in ADR 0004's shape, and everything is sorted, so a rerun gives identical rows.
* **Checks:** generated claims pass every per-file and cross-file rule, and the atlas region check, before they reach the database; the build stops otherwise.
* **Licence:** the claims go into the database the live site reads, with the Allen credit in the footer and the citation on each claim; never into the repository or the dumps.

### Consequences

* Good, because the site shows real amygdala connectivity, each connection opening its experiments.
* Bad, because absent results (densities below the threshold) aren't claims yet; that needs a decision on detection limits.
* Bad, because every build depends on the Allen API (about 45 seconds), including the required CI job: an outage blocks merging until it ends, and the previous deployment stays live. A cache (sprint 0.3d's standard packages) is the planned mitigation.
* Neutral: Cre-line experiments are a later sprint.
