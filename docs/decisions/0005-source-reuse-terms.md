---
status: proposed
date: 2026-10-03
decision-makers: Tyler Banks
consulted: Claude (research, sprint 1.1)
---

# Reuse terms of candidate data sources

## Context and Problem Statement

[ADR 0002](0002-licensing.md) licenses project-curated data under CC BY 4.0, keeps ingested data under its upstream licence (declared per path in `REUSE.toml`), and links non-commercial data instead of copying it. Before any adapter copies data (sprints 1.2–1.5) or the literature corpus is built (sprint 2.2), each candidate source's reuse terms must be known. What may Axonarium copy from each source, and on what conditions?

The terms below were read from each provider's own pages on 3 October 2026. They are a working record for the project, not legal advice, and each adapter re-checks its source's terms before it is merged.

## Considered Options

For each source, one of:

* **Copy**: store the source's data in `data/` under its upstream licence, declared in `REUSE.toml`, with the attribution it requires.
* **Link**: store only identifiers, citations and the project's own paraphrased claims; read the source's content at build time without committing or redistributing it.
* **Ask first**: neither, until the provider grants permission.

Referring to a source's identifiers (such as `MBA:295`) and citing its papers needs none of these; it is always allowed.

## Decision Outcome

| Source | Used in | Terms (as published) | Handling |
| --- | --- | --- | --- |
| [SCKAN](https://zenodo.org/records/6369432) | Sprint 1.5 | CC BY 4.0 | **Copy**, crediting SCKAN and the pinned release; `REUSE.toml` annotates its path as CC-BY-4.0 |
| [Allen Mouse Brain Connectivity Atlas](https://alleninstitute.org/terms-of-use/) and other Allen Brain Map data | Sprints 1.2, 1.3 | Allen Institute Terms of Use: "use, copy, distribute … or create derivative works of the Content … for research or other noncommercial purposes"; "You may not redistribute the Content or Improvements for commercial purposes without our written permission"; follow the [Citation Policy](https://alleninstitute.org/citation-policy/) | **Ask first, link meanwhile** (see below) |
| [BAMS](https://bams1.org/overview/policy.php) | Sprint 1.4 | © University of Southern California; no licence granted: "Please contact us before using any part of BAMS or data therein, for constructing and populating new systems" | **Ask first** (contact listed on the site). Sprint 1.4 stays blocked until permission is granted |
| BrainGlobe `allen_mouse` and `allen_human` atlases | Sprint 1.2 | Allen Institute Terms of Use (BrainGlobe repackages them; its own code is BSD-3-Clause and it records no atlas licences) | As Allen |
| BrainGlobe `whs_sd_rat` ([Waxholm Space atlas v4.01](https://www.nitrc.org/frs/shownotes.php?release_id=4822)) | Sprint 1.2 | CC BY-SA 4.0 | **Copy** atlas-derived files (hierarchy, names, meshes) under CC-BY-SA-4.0 on their own paths. Share-alike covers those files and anything derived from them, not claims that only refer to Waxholm region IDs |
| BICAN [MBA](https://github.com/brain-bican/mouse_brain_atlas_ontology) and [HBA](https://github.com/brain-bican/human_brain_atlas_ontology) ontologies | Prefixes in the schema | No licence declared; built from Allen structure graphs | Use the PURLs as identifiers only; treat their content as Allen |
| [UBERON](https://obofoundry.org/ontology/uberon.html) | Region mappings | CC BY 3.0 | Identifiers freely; copied labels or definitions keep CC-BY-3.0 with attribution |
| [Cell Ontology](https://obofoundry.org/ontology/cl.html) | Neuron types | CC BY 4.0 | Identifiers freely; copied content with attribution |
| [NCBITaxon](https://obofoundry.org/ontology/ncbitaxon.html) | Species | CC0 1.0 | No conditions |
| [Hintiryan et al. 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8129205/), mouse basolateral amygdala connectivity | Sprints 2.2–2.3 | Article: CC BY 4.0. Its [online maps](https://mouseconnectomeproject.github.io/amygdalar/) state no licence | Extract claims from the article (short excerpts allowed with credit). **Ask first** before copying the map data |
| [MouseLight](https://www.janelia.org/project-team/mouselight/neuronbrowser) single-neuron reconstructions | Neuron-type evidence | Per neuron on Janelia's figshare: older releases CC BY-NC 4.0, newer ones CC BY 4.0; the NeuronBrowser states CC BY-NC | **Copy** CC BY neurons; **link** CC BY-NC ones. Check each neuron's licence |
| [Allen Brain Cell Atlas](https://knowledge.brain-map.org/data/LVDBJAW8BI5YSS1QUBG) | Neuron-type identity | MERFISH data CC BY 4.0; 10x single-cell data CC BY-NC 4.0 | **Copy** MERFISH-derived data; **link** 10x data |
| [Europe PMC](https://europepmc.org/downloads/openaccess) and PMC open-access articles | Sprint 2.2 | Licence varies by article | Paraphrased claims and locators from any paper; verbatim `excerpt` only from CC BY or CC0 articles (the schema's rule); record each source's licence in its `Source` record |
| [Crossref metadata](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | `data/sources/` | "almost none of the metadata is subject to copyright, and you may use it for any purpose", except some abstracts | **Copy** metadata; **never** cache abstracts |
| [PubTator3](https://www.ncbi.nlm.nih.gov/research/pubtator3/) | Entity tagging | US Government work; the annotated text keeps its publishers' terms | Use annotations freely; the text follows the article's licence |
| [WhiteText corpus](https://figshare.com/articles/dataset/New_WhiteText_Corpus/1400541) | Extraction benchmark | CC BY 4.0 | **Copy** into `agents/evals/` with credit |

**Allen data needs a maintainer decision.** Its terms allow research and non-commercial use but not commercial redistribution, while project data is CC BY 4.0, which allows commercial reuse. Allen is the main v1 source for mouse regions (sprint 1.2) and region-level connectivity (sprint 1.3). Recommended, in order:

1. The maintainer asks the Allen Institute for written permission to redistribute region names, hierarchy and derived region-level connectivity claims under CC BY 4.0, with citation per its policy.
2. Until permission arrives, Allen-derived content is not committed. Adapters read it at build time; the live site and API, which are non-commercial, may serve it with the Allen citation; release dumps either leave it out or carry it in a separate file under the Allen terms.
3. If permission is refused, keep option 2 permanently and record that in a superseding ADR.

**Deferred**: sources for later modules (GMMAD, BGMDB, gutMDisorder, MICrONS, H01, FlyWire and BANC, the marmoset atlases, siibra and Julich-Brain, the Human Reference Atlas, SPARC maps, the EBRAINS Knowledge Graph) are audited when their module starts, in that module's first sprint.

### Consequences

* Good, because every adapter knows before it is written what it may copy and how to annotate it in `REUSE.toml`.
* Good, because SCKAN, Waxholm, the ontologies, WhiteText, Crossref metadata and CC BY literature are usable now.
* Bad, because the Allen terms keep the main mouse source out of committed data until permission is granted, which shapes sprints 1.2 and 1.3.
* Bad, because BAMS stays blocked until its maintainers agree.
* Neutral: a new licence reference (such as one for the Allen terms) is added to `LICENSES/` only when a file under it is first committed, because `reuse lint` rejects unused licences.

### Confirmation

Each adapter's pull request cites the row of this table it relies on and re-checks the source's terms on that date. Maintainer actions arising from this ADR: contact the Allen Institute and BAMS for permission, and choose the Allen handling above.
