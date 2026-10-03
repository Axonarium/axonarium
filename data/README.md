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
| `entities/atlases/` | Pinned atlas versions | `<id>.yaml` |
| `entities/regions/` | Regions | the ID with `:` as `_`, such as `MBA_295.yaml` |
| `entities/neuron_types/` | Neuron types | `<id>.yaml` |
| `sources/` | Cached paper metadata (filled in sprint 0.3b) | not fixed yet |
| `retractions.yaml` | The log of deleted and retracted claims | fixed |
| `allowlist.yaml` | Accepted evidence source types; human-owned (sprint C.2) | fixed |

Edges are computed from claims at build time and are never edited by hand.

## Checks

Run these before pushing a change to this folder; pre-commit and CI run them too.

```bash
uv run python -m checks files                       # every file here
uv run python -m checks changes --base origin/main  # what your branch changes
```

Each problem prints as `<path>: <rule-id>: <message>`.

| Rule | Means |
| --- | --- |
| `yaml-error`, `duplicate-key` | The file isn't valid YAML, or repeats a key |
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
| `deletion-unlogged`, `retraction-unlogged` | A claim was deleted or retracted without a new entry in `retractions.yaml` |
| `log-rewritten` | An existing entry in `retractions.yaml` was edited, reordered or removed |

## Deleting or retracting a claim

Add an entry to `retractions.yaml` in the same pull request, giving the claim's ID, `deleted` or `retracted`, a reason, and who decided. Never edit or remove existing entries. The maintainer owns that file, so these pull requests always need their review ([ADR 0006](../docs/decisions/0006-deletion-and-retraction-review.md)).
