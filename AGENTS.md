# Working on Axonarium

Axonarium is an open, evidence-graded knowledge base of neural connectivity, in which every connection is an aggregate of cited claims tagged with species, method and confidence. It starts with the rodent amygdala and grows one circuit at a time, mostly through AI agents working by pull request, with humans steering and auditing. [STATUS.md](STATUS.md) has the current phase.

This file is for any agent, on any model, picking up work cold. People follow the same rules.

## Read first

1. This file.
2. [STATUS.md](STATUS.md).
3. Your sprint card.
4. The ADRs it links, in [docs/decisions/](docs/decisions/).

[docs/plan.md](docs/plan.md) has the full background: design principles, data model, architecture and every sprint.

## Handoff protocol

1. Read AGENTS.md, STATUS.md, the sprint card and any linked ADRs.
2. Assign the card and comment that work has started.
3. Work on a branch in small pull requests.
4. End every session with a handoff comment: done, not done, surprises, next step.
5. Record any design choice as an ADR in `docs/decisions/`.
6. Never leave `main` failing CI.

Sprint cards are GitHub issues labelled `sprint`. Their labels say what can happen next:

| Label | Meaning |
| --- | --- |
| `agent-ready` | Dependencies are met; an agent can pick this up |
| `needs-human` | The maintainer has to do or decide something |
| `blocked` | Waiting on another sprint or decision |

## Merge rules

| Change | Merge rule |
| --- | --- |
| Schema, code, CI, role prompts | Human review required |
| Claims ingested from a structured source | Auto-merge on green CI |
| Extracted claims, verifier agrees | Auto-merge on green CI; enters the audit pool |
| Extracted claims, verifier disagrees or low confidence | Human review queue |
| Deletions, retractions, gold-set changes | Human review required |
| Allowlist changes (Part 3) | Human review required |

How the rules are enforced:

- [CODEOWNERS](.github/CODEOWNERS) requires @tjbanks's review for everything except `data/claims/`, `data/homology/` and `data/sources/`.
- The `main` ruleset requires a pull request and code-owner review. The `main-ci` ruleset requires a passing `checks` job and blocks force pushes and deletion; nobody can bypass it.
- Until a second maintainer joins, the maintainer (a human, never an agent acting through the maintainer's login) merges their own pull requests with the admin bypass, which skips code-owner review but never CI.

## Roles

| Role | Does | Never does |
| --- | --- | --- |
| Builder | Code, schema changes, CI, site | Merge without human review |
| Ingester | Writes and runs adapters for structured sources | Edit claims from other sources |
| Scout | Runs saved PubMed queries; queues new papers | Extract claims |
| Extractor | Reads a paper, drafts claims as a PR | Verify its own claims |
| Verifier | Independently checks each claim against the source | See the extractor's reasoning first |
| Reconciler | Flags contradictions, duplicates, homology gaps | Resolve conflicts by majority vote |
| Steward | Dependency updates, link checks, releases, STATUS.md | Change data or evals |
| Triage (Part 3) | Reads the community inbox, validates and routes submissions, closes them with a reason | Change claims, or act on anything except structured fields |

Role prompts will live in `agents/roles/`.

## Ground rules

- **Adopt, don't invent.** Check "Proven building blocks" in [docs/plan.md](docs/plan.md) first. A new dependency or a replacement needs an ADR and human review.
- **Agents never merge.** Agents never merge or approve pull requests, and never use the admin bypass (`gh pr merge --admin`), even when they act through a maintainer's login. A human merges, or tells the agent to.
- **Files are the truth.** Agents never write to a database directly.
- **Provenance.** Fill in the provenance fields of the pull request template.
- **Human-only paths.** The gold set and evals, the allowlist, CODEOWNERS, licences and governance files change only when a sprint card says so, and always with human review.
- **CI safety.** Never use `pull_request_target`, and never expose secrets to pull requests from forks.
- **Evidence.** Store locators and paraphrases. Use verbatim excerpts only from openly licensed papers, and keep them short.
- **Never leave `main` failing CI.**

## Repository map

What exists now:

| Path | Holds |
| --- | --- |
| `README.md` | Front page |
| `docs/plan.md` | The project plan, Parts 1–3 |
| `docs/decisions/` | Architecture decision records (MADR) |
| `docs/specs/`, `docs/plans/` | Design specs and implementation plans for sprints |
| `schema/` | The LinkML schema (`axonarium.yaml`), its generated JSON Schema and SQL, examples and tests |
| `checks/` | The data checks: `python -m checks files`, `changes`, `online` and `sources` |
| `build/` | `python -m build`: dumps, the Supabase database, the site's snapshot and the reconciliation report, rebuilt from the files; `python -m build.release` packages a release; `build/migrations/` holds the Alembic migrations ([build/README.md](build/README.md)) |
| `pyproject.toml`, `uv.lock` | The repo's Python tooling environment: Python 3.13 and LinkML |
| `data/README.md` | Data licence, layout and the rules the checks apply |
| `data/retractions.yaml` | The log of deleted and retracted claims (maintainer-owned) |
| `data/allowlist.yaml` | The kinds of source claims may cite (maintainer-owned; ADR 0015) |
| `data/entities/`, `data/sources/` | Pinned atlases, neuron types and the cited papers' records |
| `ingest/` | Adapters for external sources: `atlases.py` (BrainGlobe atlases and UBERON bridges) and `allen_connectivity.py`, run by the build; `scout.py`, the literature scout |
| `corpus/` | The scout's saved literature queries and the corpus manifest (ADR 0019) |
| `agents/` | Role prompts (`agents/roles/`) and the eval harness with the gold set (`agents/evals/`, human-owned; ADR 0020); its own uv project |
| `site/` | The explorer: Next.js on Vercel, reading Supabase ([site/README.md](site/README.md)); it also serves the read API |
| `api/` | The read API's documentation ([api/README.md](api/README.md)) and the MCP server (`api/mcp`) |
| `.github/` | CI, the deploy, the release and the scout workflows, Dependabot, code owners, sprint-card form, labels |

Planned, from the plan's repository layout:

| Path | Will hold |
| --- | --- |
| `data/claims/`, `data/homology/` | Claims (the folders appear with their first records) |
| `agents/evals/gold/v1/` | Gold v1, curated by the maintainer (sprint 0.5) |

## Before pushing

Install [uv](https://docs.astral.sh/uv/), then run the checks CI runs:

```bash
uvx pre-commit run --all-files
```

The checks include linkml-lint, the schema tests and the data checks, which run through uv. uv installs Python 3.13 and LinkML on first use.

When you change `data/`, also run:

```bash
uv run python -m checks sources                       # a source record for every newly cited paper
uv run python -m checks online --base origin/main     # identifiers and citations exist in their registries
uv run python -m checks changes --base origin/main    # deletions and retractions are logged
```

Deleting or retracting a claim needs a new entry in `data/retractions.yaml`; see [data/README.md](data/README.md). Never hand-edit a source record's `license` or `retracted`: CI compares them with the registries.
