---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# Atlas layer: BrainGlobe at build time, UBERON bridges for mappings

## Context and Problem Statement

Claims name regions in pinned atlas versions (plan: Data model), and the site needs region names, hierarchies and, later, meshes. Allen atlas content can't be committed until the Allen Institute grants permission (ADR 0005); the Waxholm rat atlas is CC BY-SA 4.0, which project data (CC BY 4.0) can't absorb. Regions also need UBERON terms, so claims in different atlases and species can be compared. Where do regions and their mappings come from?

## Considered Options

* BrainGlobe at build time for regions, and UBERON's published bridges for mappings
* Region records committed to `data/`, with a hand-curated mapping file
* The Allen API for each atlas, with UBERON cross-references looked up per term

## Decision Outcome

Chosen option: "BrainGlobe at build time and UBERON's bridges", because both are the standard, maintained sources, and nothing restricted ends up in the repository.

* **Atlases:** pinned atlas records in `data/entities/atlases/`, each naming its BrainGlobe atlas and the atlas data version (`extra.brainglobe.atlas_version`). The build asks BrainGlobe for exactly that version (`BrainGlobeAtlas(name, version=…)`; BrainGlobe keeps old versions) and stops if it gets another, so an atlas update is a reviewed change and BrainGlobe's releases never break the build.
  * `allen-mouse-ccf-2017`: `allen_mouse_25um` 3.1, Wang et al. 2020, `MBA:` IDs.
  * `allen-human-3d-2020`: `allen_human_500um` 3.1, Ding et al. 2016, `DHBA:` IDs (Allen structure graph 16; new in schema 0.3.0).
  * `waxholm-sd-rat-v4`: `whs_sd_rat_39um` 3.0, Kleven et al. 2023. It has no amygdala nuclei (one "Amygdaloid area, unspecified"), so it contributes no region IDs; rat claims name UBERON terms. It is pinned for its meshes.
* **Regions:** `ingest/atlases.py` reads each pinned atlas with `brainglobe-atlasapi` and gives one row per structure (name, acronym, parent). Parents come from each structure's ID path, because BrainGlobe 3.0.2 stores parent IDs as 16-bit integers and wraps those above 65535; every parent must be a region of the same atlas. They go into the database, which the live, non-commercial site reads with the atlas citation; they stay out of the dumps (ADR 0005).
* **Mappings:** UBERON's `uberon-bridge-to-mba.owl` and `uberon-bridge-to-dhba.owl` (CC BY 3.0) from release `v2026-10-01`, each pinned by SHA-256, read with rdflib: a region maps to a UBERON class when its equivalent class is exactly that class restricted to a species. Layer- or part-specific equivalences map to nothing rather than to a broader term. UBERON doesn't map every region (for example the human atlas's BL and Me).
* **Amygdala:** a region belongs to the amygdala when UBERON places its term under the amygdala (UBERON:0001876, is-a or part-of, as OLS computes it). The build stores that flag and the term's label in the `regions` table, so the site keeps no list of its own.
* **Checks:** the build stops when data names an `MBA:`, `HBA:` or `DHBA:` region its atlas doesn't have (including atlases loaded without regions, such as Waxholm), or an atlas resolves no amygdala region. `--no-atlases` skips loading for offline work and tests, and refuses to load a database, which it would leave without atlas regions.

### Consequences

* Good, because claims are checked against the exact atlas version they cite, and mappings follow UBERON's curators rather than ours.
* Good, because the repository holds identifiers only; Allen and Waxholm content is read when the database is built.
* Bad, because every build needs BrainGlobe's S3 and the UBERON PURLs; an outage stops the build and the previous deployment stays live.
* Bad, because rat amygdala nuclei have no open atlas regions; rat claims are coarser in 3D until one exists.
* Neutral: meshes for the 3D view come from the same pinned atlases in sprint 3.3b.
