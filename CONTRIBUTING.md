# Contributing to Axonarium

Thank you for helping map how the brain and body are wired. People and AI agents contribute the same way: through pull requests on GitHub.

## How changes happen

- All changes arrive as pull requests. Nothing is edited in place, including the data.
- Read [AGENTS.md](AGENTS.md) first. Its handoff protocol and merge rules apply to people as well as agents.

## Conduct

Follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report conduct concerns to [admin@axonarium.com](mailto:admin@axonarium.com).

## Credit

To be credited, include your ORCID iD in your first pull request. Curation records identify human contributors by ORCID.

## Before you push

Install [uv](https://docs.astral.sh/uv/), then run the same checks CI runs:

```bash
uvx pre-commit run --all-files
```

## Reporting problems

Report bugs, wrong claims and missing evidence in [GitHub issues](https://github.com/axonarium/axonarium/issues).
