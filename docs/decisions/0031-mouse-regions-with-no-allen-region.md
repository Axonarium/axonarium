---
status: accepted
date: 2026-10-15
decision-makers: Tyler Banks
consulted: Claude (review queue, #116)
---

# Mouse claims name a UBERON term where no single Allen region fits

## Context and Problem Statement

Mouse claims name Allen Mouse Brain Atlas regions, and the extractor could name nothing else for mouse (`Lexicon.entity`, ADR 0028). Some regions that papers test have no single Allen region. Allen has no medial prefrontal cortex, no amygdala as a whole and no substantia nigra, and it splits the superior colliculus into its sensory and motor parts. So a paper's "mPFC" became either one subregion, which is narrower than the paper, or Isocortex, which is far broader. The verifier disagreed with or doubted 15 such claims in the first review queue (#116, questions 1, 2 and 4). How should a mouse claim name these regions?

## Considered Options

* Name the Allen subregion the evidence is in when the paper says which, and otherwise the UBERON term
* Name the subregion, and leave the claim out when the paper doesn't say which
* Allow UBERON terms for mouse claims everywhere

## Decision Outcome

Chosen option: "the Allen subregion when the paper says which, otherwise the UBERON term". It keeps the claim at the paper's own scope. Leaving the claim out would lose much of the mouse literature on mPFC, and allowing UBERON everywhere would split one region between two IDs.

* A mouse claim may name a UBERON term only when no mouse Allen region maps to it through UBERON's bridge (ADR 0009). The extractor drops a mouse claim naming a term that an Allen region maps to, and reports it.
* The prompt's table of names (`agents/roles/extractor.md`, from `extract@0.4.0`) lists the terms to use: medial prefrontal cortex (UBERON:4450000), prefrontal cortex, insular cortex, superior colliculus, substantia nigra, amygdala, basal forebrain and preoptic area. It tells the extractor never to widen such a region to Isocortex, Midbrain or Striatum.
* The amygdalostriatal transition area has no UBERON term or Allen region of its own. It is named as the striatum-like amygdalar nuclei: MBA:278 in mouse, UBERON:8440030 in rat.
* Rat claims are unchanged: they name UBERON terms already.

### Consequences

* Good, because a paper's "mPFC" or "superior colliculus" is recorded at the scope the paper gives, so the verifier has nothing to object to.
* Good, because rat and mouse claims about such a region share a term.
* Bad, because a mouse region can now appear under two IDs: a UBERON term from one paper, and an Allen subregion of it from another. Rolling claims up to a parent needs the UBERON hierarchy, not just Allen's.
* Neutral: claims written before `extract@0.4.0` keep their broader or narrower Allen region until their papers are read again.
