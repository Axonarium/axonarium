# Data

This directory holds Axonarium's knowledge as small YAML files. The files are the source of truth: the database, dumps, site and API are rebuilt from them. The full model is in [docs/plan.md](../docs/plan.md), Part 1, "Data model".

## Licence

Project-curated data in this directory is licensed under [CC BY 4.0](../LICENSES/CC-BY-4.0.txt). Data ingested from other sources keeps its upstream licence, declared per path in [REUSE.toml](../REUSE.toml).

## Layout

Each record is one YAML file. Its folder decides its class in [the schema](../schema/axonarium.yaml), and its file name must match its ID.

| Path | Holds | File name |
| --- | --- | --- |
| `claims/<module>/` | Connectivity claims, by module such as `amygdala` | `<id>.yaml`, such as `clm-pq22bk4dtz.yaml` |
| `homology/` | Cross-species homology claims | `<id>.yaml` |
| `entities/atlases/` | Pinned atlas versions: the BrainGlobe atlas, its data version in `extra.brainglobe.atlas_version`, and its citation. Their regions are read at build time, never committed ([ADR 0009](../docs/decisions/0009-atlas-layer.md)) | `<id>.yaml` |
| `entities/regions/` | Regions of atlases BrainGlobe doesn't provide. Allen (`MBA:`, `HBA:`, `DHBA:`) regions come from the pinned atlases at build time and are never committed ([ADR 0005](../docs/decisions/0005-source-reuse-terms.md), [ADR 0009](../docs/decisions/0009-atlas-layer.md)) | the ID with `:` as `_` |
| `entities/neuron_types/` | Neuron types | `<id>.yaml` |
| `sources/<scheme>/` | Paper metadata, one record per cited paper, keyed by its DOI, else PubMed ID, else PMC ID, else arXiv ID; written by `checks sources` from Crossref, DataCite or NCBI, including the paper's `kind` (journal article, preprint, dataset or other) | the ID with `:` and `/` as `_`, other characters outside letters, digits and `.()-` %-encoded: `doi_10.1038_s41467-021-22915-5.yaml` |
| `retractions.yaml` | The log of deleted and retracted claims | fixed |
| `allowlist.yaml` | The kinds of source claims may cite, such as journal articles and bioRxiv preprints; the maintainer owns it ([ADR 0015](../docs/decisions/0015-source-allowlist.md)) | fixed |

Edges are computed from claims at build time and are never edited by hand.

## Checks

Run these before pushing a change to this folder; pre-commit and CI run them too.

```bash
uv run python -m checks sources                     # write a source record for every newly cited paper
uv run python -m checks files                       # every file here
uv run python -m checks online --base origin/main   # look up what your branch changed (needs the network)
uv run python -m checks changes --base origin/main  # what your branch deleted or retracted
```

`checks online` asks EBI OLS (UBERON, Cell Ontology, NCBITaxon), the Allen Brain Map API (MBA, HBA), doi.org, Crossref, DataCite and NCBI (PubMed, PubMed Central). It caches answers for 7 days in `.cache/checks/`, and fails rather than passes when a registry can't be reached ([ADR 0007](../docs/decisions/0007-online-identifier-checks.md)). `checks sources --refresh` re-fetches every DOI record, for example after a retraction.

Each problem prints as `<path>: <rule-id>: <message>`.

| Rule | Means |
| --- | --- |
| `yaml-error`, `duplicate-key` | The file isn't valid UTF-8 YAML, uses anchors or aliases, or repeats a key |
| `symlink` | A symbolic link instead of a real file |
| `unknown-location` | The file isn't in a folder above (`.yml` files included) |
| `schema` | The record breaks the schema for its folder's class |
| `file-name` | The file name doesn't match the ID |
| `extra-mapping`, `extra-key` | `extra` must be a mapping with namespaced keys, like `lab.tracer` |
| `empty-text` | A text field is empty or only spaces |
| `non-finite` | A number is NaN or infinite |
| `uncertainty` | A negative SD or SEM, or a confidence interval missing a bound or reversed |
| `unit` | A measurement's unit or range doesn't fit its quantity |
| `absent-result` | An absent result with a strength, measurements or a sign |
| `role` | A role that doesn't fit who did the work |
| `independent-verifier` | An agent verified a claim with the same prompt that extracted it |
| `doi-case` | A DOI isn't lowercase |
| `homology-pair` | A homology claim within one species, or between a region and a neuron type |
| `neuron-type-region` | A neuron type's region isn't a region |
| `duplicate-id` | Two files share an ID |
| `unknown-reference` | A neuron type or atlas that has no record here |
| `atlas-species` | A claim's species doesn't match the atlas its regions come from |
| `missing-source` | A claim's paper has no record in `sources/` |
| `cites-retracted` | A claim cites a retracted paper but isn't itself `retracted` (online too, when PubMed lists a cited PubMed ID as retracted) |
| `excerpt-licence` | A claim has a verbatim excerpt, but its source isn't CC BY or CC0 |
| `source-not-allowed` | A claim's source is a kind of publication, or from a venue, that `allowlist.yaml` doesn't accept |
| `unknown-term`, `obsolete-term` | An ontology term or atlas structure doesn't exist, or is obsolete (online) |
| `unknown-citation`, `citation-mismatch` | A DOI, PubMed, PubMed Central or arXiv ID doesn't exist, or the IDs of one citation name different papers (online) |
| `citation-incomplete` | A citation lacks the DOI or PubMed ID that its PubMed or PubMed Central record names; add it (online) |
| `source-outdated` | A source record's kind, journal, licence or retraction status differs from its registry; run `checks sources --refresh` (online) |
| `lookup-failed` | A registry couldn't be reached; re-run when it is back (online) |
| `deletion-unlogged`, `retraction-unlogged`, `restoration-unlogged` | A claim was deleted, retracted, or restored from retraction without a new entry in `retractions.yaml` |
| `log-rewritten` | An existing entry in `retractions.yaml` was edited, reordered or removed |

## Retracted papers

When a cited paper is retracted, `checks sources --refresh` marks its record `retracted: true` (if Crossref or PubMed says so; PubMed Central and arXiv records carry no retraction status); each claim citing it must then be set to `status: retracted`, with a `retracted` entry in `retractions.yaml`. Claims are flagged, never silently deleted.

## Deleting or retracting a claim

Add an entry to `retractions.yaml` in the same pull request, giving the claim's ID, `deleted`, `retracted` or `restored`, a reason, and who decided. Never edit or remove existing entries. The maintainer owns that file, so these pull requests always need their review ([ADR 0006](../docs/decisions/0006-deletion-and-retraction-review.md)).
