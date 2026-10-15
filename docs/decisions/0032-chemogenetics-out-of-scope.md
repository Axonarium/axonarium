---
status: accepted
date: 2026-10-15
decision-makers: Tyler Banks
consulted: Claude (review queue, #116)
---

# Chemogenetic results are not extracted as connectivity claims

## Context and Problem Statement

Papers often test a pathway with DREADDs: hM3Dq or hM4Di in one region, activated by CNO or C21, with Fos, behaviour or a recording read elsewhere. The schema's evidence classes have no place for this, so `extract@0.3.0` recorded such results as `optogenetic_circuit_mapping`, and the verifier disagreed with all of them (4 claims in #116, question 5). Should chemogenetics get an evidence class, or be left out?

## Considered Options

* Leave chemogenetic results out of extraction
* Add an evidence class for chemogenetic manipulation (a schema change)

## Decision Outcome

Chosen option: "leave them out". Activating a whole population for minutes, then counting Fos or scoring behaviour, rarely shows which region the effect passed through, so a `functionally_connects_to` claim from it would mostly record polysynaptic effects. `extract@0.4.0` tells the extractor to leave them out, and the four claims from #116 were deleted.

### Consequences

* Good, because no schema change is needed, and the evidence that is extracted keeps one meaning per class.
* Bad, because a chemogenetic experiment that does isolate a pathway, such as CNO infused at the terminals, is lost too. An evidence class for it can come later through a new ADR if such papers turn out to matter.
