# Axonarium

An open, cited map of how the brain and body are wired.

Axonarium is an open, AI-maintained map of how the brain is wired, where every connection is backed by a cited source, tagged by species and method, and exportable straight into simulations. It starts with the amygdala and is built to grow across the whole brain and body, giving neuroscientists and AI builders a trustworthy, machine-readable answer to how real circuits connect across rat, mouse and human.

## Status

Pre-alpha: the project is in Phase 0, Foundations. See [STATUS.md](STATUS.md).

## How it works

- Knowledge lives as small YAML claim files in this repository. Each claim is one cited statement about one connection in one species.
- People and scheduled AI agents change it only through pull requests that pass CI.
- The database, data dumps, site and API are rebuilt from the files.

## Find your way around

- [docs/plan.md](docs/plan.md): the project plan
- [AGENTS.md](AGENTS.md): how work happens here, for agents and people
- [STATUS.md](STATUS.md): the current phase, sprints and open decisions
- [docs/decisions/](docs/decisions/): architecture decision records
- [SUCCESSION.md](SUCCESSION.md): who holds which account

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Citing

Cite Axonarium with the metadata in [CITATION.cff](CITATION.cff). GitHub's "Cite this repository" button reads it.

## Licences

- Code and docs: Apache-2.0 ([LICENSE](LICENSE)).
- Project-curated data: CC BY 4.0 ([data/README.md](data/README.md)).
- Per-path details, including data from other sources: [REUSE.toml](REUSE.toml).

## Contact

[admin@axonarium.com](mailto:admin@axonarium.com)
