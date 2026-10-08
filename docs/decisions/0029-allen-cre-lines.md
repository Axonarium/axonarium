---
status: accepted
date: 2026-10-08
decision-makers: Tyler Banks
consulted: Claude (sprint 1.7)
---

# Allen's Cre-line experiments join the region-level claims

## Context and Problem Statement

The Allen adapter (ADR 0010) used only wild-type experiments: 22 with an injection in the amygdala, and 153 elsewhere that label it. A further 53 amygdala experiments, and many more elsewhere, use Cre driver lines. A Cre-dependent tracer labels only the neurons expressing Cre, so ADR 0010 left them for neuron-type claims. They cost no model tokens and fill much of the mouse graph, including amygdala regions no wild-type injection reached. What should they say before neuron types can be mapped to Cre lines (an open question of the inventory, sprint 2.1)?

## Considered Options

* Region-level claims from Cre-line experiments too, each recording its line
* Wait until Cre lines map to neuron types, then make neuron-type claims only

## Decision Outcome

Chosen option: "region-level claims, each recording its line". Labelled axons in a target show that neurons of the injected region project there, whichever of its neurons carry them. So a Cre-line experiment supports the same region-level claim as a wild-type one, from a subset of the region's neurons. Recording the line keeps the subset visible, and lets neuron-type claims be made from the same experiments once the mapping exists.

* Experiments: every Mouse Connectivity Projection experiment that passed QC with a single injection, wild-type or Cre-line. The rest of ADR 0010 is unchanged: targets, the 0.01 density floor, spill-over, and `proposed` status when under half the injection is in the named region.
* Each claim from a Cre-line experiment records `allen.transgenic_line` in `extra` (the donor's lines, `;`-separated), and its paraphrase says the tracer was Cre-dependent.
* The adapter's procedure becomes `allen-connectivity@1.3.0`. Claim IDs, from experiment and target, are unchanged.

### Consequences

* Good, because the amygdala's outputs come from about three times as many experiments, and its inputs from many more, at no model cost.
* Good, because gap mode's untested regions shrink where a Cre-line injection reached one, and the reconciliation report sees more agreement and silence.
* Bad, because a Cre-line density measures a subpopulation's axons. A connection's strongest density stays a fair summary, but a density from a sparse line understates the region's projection. The line is recorded so a reader can tell.
* Neutral: neuron-type claims from these experiments wait for the inventory's mapping from Cre lines to neuron types.
