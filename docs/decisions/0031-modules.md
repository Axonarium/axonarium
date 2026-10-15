---
status: accepted
date: 2026-10-15
decision-makers: Tyler Banks
consulted: Claude (hippocampus and prefrontal modules)
---

# Modules: the amygdala, the hippocampus and the prefrontal cortex, and a species switch

## Context and Problem Statement

Axonarium starts with the amygdala and grows one circuit at a time (plan, principle 7, "One module at a time"). The maintainer chose the hippocampus and the prefrontal cortex as the next two, and asked for rat and mouse on the explorer (15 October 2026). Today "the amygdala" is a single UBERON root (`UBERON:0001876`, ADR 0009), a boolean `amygdala` column on `regions`, the Allen adapter's injection sites (ADR 0010), gap mode's untested regions (ADR 0027), the claims folder `data/claims/amygdala/`, and the brain page, which draws the mouse only. How does a second and third circuit join without copying each of those?

The plan's gate rule ("a new module starts only after the previous gate passes") is relaxed for code only: the maintainer chose to build modules now and to hold the new modules' extraction runs until the amygdala's audit (sprint 2.5) shows the extractor's precision.

## Considered Options

* A module file in `data/`, each module a UBERON root plus listed regions
* One boolean column per module (`amygdala`, `hippocampus`, `prefrontal`), as today
* Module membership written into the code, a constant per module

## Decision Outcome

Chosen option: "a module file in `data/`", because the prefrontal cortex can't be found from UBERON alone, so membership has to be a reviewed, curated list somewhere, and a data file is reviewed, versioned and released like the rest of the data. Columns per module change the database schema for every module; constants hide a curation decision in code.

* **The file:** `data/modules.yaml`, a `ModuleList` in the schema. The maintainer owns it (CODEOWNERS), like the allowlist. Each module has an `id`, a `name`, and any of:
  * `roots`: UBERON terms; a region belongs when its term is a root or under one (is-a or part-of, as OLS computes it), as for the amygdala today;
  * `regions`: atlas regions that belong although UBERON doesn't place them under a root;
  * `exclude`: atlas regions or UBERON terms that a root takes in but the module doesn't want, such as fibre tracts.
* **Membership:** an atlas region belongs to a module when it, or a region it is part of, is a member by the rules above (subdivisions follow their parent, as `amygdala_structures` does now). A UBERON term, which rat claims name, belongs when it is under a root, is listed, or is the term a member atlas region maps to. A region can belong to more than one module.
* **The first three modules:**
  * `amygdala`: root `UBERON:0001876`. Unchanged: the same 11 Allen regions and their subdivisions.
  * `hippocampus`: root `UBERON:0002421`, the hippocampal formation. In the Allen atlas that is HPF (`MBA:1089`): CA1–3, the dentate gyrus, the subiculum and the retrohippocampal region, entorhinal cortex included. The fibre tracts UBERON places under it (fornix, fimbria, alveus) are excluded.
  * `prefrontal`: root `UBERON:0000451`, which finds only PL and ILA in the Allen bridge, plus the regions ACA (`MBA:31`), ORB (`MBA:714`) and FRP (`MBA:184`), and the terms for anterior cingulate and orbitofrontal cortex for rat claims. Whether the agranular insula joins is the maintainer's call; it starts out.
* **Database and API:** `regions` gains `modules`, a text array set by the build (subdivisions included). A `modules` table holds the file's modules in order, with the UBERON terms each resolves to, for rat claims. The `amygdala` column and the API's `amygdala` field and filter stay as they are (UBERON places the region's own term under the amygdala), so `/api/v1` clients don't break; `/api/v1/regions?module=` and a `modules` field are added. The MCP server's region search takes a module and says which modules a region is in. Dumps gain `modules.json` and `modules.csv`.
* **Allen connectivity:** the adapter (ADR 0010, ADR 0029) loads each module's outputs (injections in it) and inputs (injections elsewhere that label it), with the same rules. A claim found for two modules is one claim: IDs come from experiment and target. Outputs are read 50 experiments a query, only densities of at least 0.01 (the claims' own floor), instead of one query per experiment; the claims are the same.
* **Gap mode:** untested regions are looked for in every module, not only the amygdala (ADR 0027 is otherwise unchanged).
* **Claims folders:** the literature pipeline writes claims to `data/claims/<module>/`, the module whose saved queries found the paper (the corpus query gains a `module`); a paper found by several modules' queries goes to the first of them in the file's order. The folder records which run read a paper, nothing more: the site and API place a connection by its regions, so a BLA → PL claim stored under `amygdala/` shows in the prefrontal module too. Claims already in `data/claims/amygdala/` stay where they are.
* **The explorer:** the brain page gets a module switch and a species switch (mouse, rat), both kept in its URL. A module's outputs and inputs are drawn relative to its regions. Region pages and lists show each region's modules. Human stays off the switch until there is human connectivity (Phase 7c).
* **Rat in 3D:** the network view draws rat claims by their UBERON terms with no new data. The 3D view draws them on the Waxholm rat atlas, already pinned for its meshes (ADR 0009), through a reviewed mapping from UBERON terms to Waxholm structure IDs (IDs only, no Waxholm names). A term with no Waxholm structure of its own takes its nearest broader one, and the view says so: the amygdala's nuclei share Waxholm's one amygdaloid area. Waxholm's meshes are CC BY-SA 4.0: like Allen's they are made at deploy and never committed, and the page names their licence and citation. The mapping and the Waxholm meshes come in their own pull request.

### Consequences

* Good, because a fourth module is a reviewed entry in `data/modules.yaml`, saved queries and an inventory, with no change to the schema, the database or the explorer.
* Good, because the claims already extracted count for every module they touch: 359 of the literature claims already name a prefrontal region and 180 a hippocampal one.
* Good, because the API keeps every field and filter it had.
* Bad, because the Allen adapter reads many more experiments: the prefrontal cortex and the hippocampus are among Allen's most injected regions. Build time and the number of build-time claims grow several-fold.
* Bad, because the prefrontal module's boundary is a curated list, so it can be argued with; it is in one reviewed file for that reason.
* Neutral: the claims folder no longer says which regions a claim is about. It never fully did: the extractor records every connection a paper tests.

### Confirmation

The build's tests cover membership from roots, listed regions and exclusions, and that the amygdala module resolves exactly the regions the `amygdala` flag did. The build stops when a module resolves no region in the Allen mouse atlas, as it does now for the amygdala. CI's `alembic check` covers the new column and table.
