# Data

This directory holds Axonarium's knowledge as small YAML files. The files are the source of truth: the database, dumps, site and API are rebuilt from them. The full model is in [docs/plan.md](../docs/plan.md), Part 1, "Data model".

## Licence

Project-curated data in this directory is licensed under [CC BY 4.0](../LICENSES/CC-BY-4.0.txt). Data ingested from other sources keeps its upstream licence, declared per path in [REUSE.toml](../REUSE.toml).

## Layout (planned)

| Path | Holds |
| --- | --- |
| `entities/` | Regions, neuron types, species and atlases |
| `claims/` | One YAML file per claim, sharded by module |
| `homology/` | Cross-species homology claims |
| `sources/` | Cached DOI metadata |
| `allowlist.yaml` | Accepted evidence source types; human-owned |

Edges are computed from claims at build time and are never edited by hand.
