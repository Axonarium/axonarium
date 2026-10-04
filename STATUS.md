# Status

Hand-maintained until the Steward role generates it (Phase 6). Last updated 4 October 2026.

## Phase

Phase 0, Foundations: in progress. Gate 0 passes when a full rebuild from empty passes, the gold set is frozen and the eval harness runs.

## Sprints

Sprint cards are [GitHub issues labelled `sprint`](https://github.com/axonarium/axonarium/issues?q=is%3Aissue%20label%3Asprint).

| Sprint | State |
| --- | --- |
| 0.1 Repo scaffold | Done |
| 0.2 Schema v0.1 in LinkML | Done |
| 1.1 License audit | Done |
| 0.3 Validation CI | Done |
| 0.3b Online identifier checks | Done |
| 0.3c Retraction status for citations without a DOI | Done |
| 0.4 Rebuild pipeline | Done |
| 1.2 Atlas layer | Done |
| 1.3 Allen mouse connectivity | Done: 2,053 build-time claims (717 accepted), 1,039 connections, the amygdala's outputs and inputs |
| 3.3a Site shell on Vercel | Done: https://axonarium.vercel.app |
| 3.3b 3D brain view | Done: `/brain`, the mouse amygdala's projections over BrainGlobe meshes |
| 3.3c Network view | Done: a linked force-directed graph on `/brain` |
| 3.1 Read API | Done: `/api/v1` with an OpenAPI 3.1 contract, reuse terms on every claim ([ADR 0013](docs/decisions/0013-read-api.md)) |
| 3.4 MCP server | Done: `api/mcp`, four read-only tools over the API ([ADR 0014](docs/decisions/0014-mcp-server.md)) |
| 4.1 SONATA export ([#50](https://github.com/axonarium/axonarium/issues/50)) | On hold until there is more data (maintainer, 4 October 2026); the first form will be a bmtk PopNet population model |
| 3.3d Region pages | Done: `/regions`, a filterable index, and `/regions/<id>`, each region's inputs and outputs with evidence |
| 0.3d Standard packages for the HTTP fetcher | Done: requests-cache, urllib3 Retry and requests-ratelimiter ([ADR 0012](docs/decisions/0012-http-packages.md)) |
| 0.5 Gold set | Waiting on the maintainer |
| C.2 Allowlist file, CODEOWNERS entry and ADR | Ready, but needs the maintainer |
| 1.4 BAMS rat adapter | Blocked until BAMS grants permission ([ADR 0005](docs/decisions/0005-source-reuse-terms.md)) |
| 0.6 and 1.6 | Blocked on earlier sprints |
| 1.5 SCKAN adapter | Ready for an agent |

Later phases get cards when they start.

## Decided

- v1 scope: rat and mouse amygdala at region and neuron-type level, with human homology, SONATA export and a resource paper.
- Stack: GitHub as the source of truth, then Supabase, then Next.js on Vercel, with shadcn/ui, React Three Fiber and react-force-graph, plus an MCP server for agents.
- The nine design principles in [docs/plan.md](docs/plan.md), including "adopt, don't invent".
- Community input: identifier-only evidence for or against a claim, with an allowlist and three defensive layers.
- Name: Axonarium ([ADR 0003](docs/decisions/0003-project-name.md)). Licences: Apache-2.0 for code and CC BY 4.0 for data ([ADR 0002](docs/decisions/0002-licensing.md)).
- Identifiers: w3id.org base URI, and a type prefix plus 10 random characters for claims and neuron types ([ADR 0004](docs/decisions/0004-identifiers.md)).
- Source reuse terms: copy, link or ask first, per source; Allen data is read at build time until the Allen Institute grants permission ([ADR 0005](docs/decisions/0005-source-reuse-terms.md)).
- Deletions and retractions: logged in data/retractions.yaml, which the maintainer owns ([ADR 0006](docs/decisions/0006-deletion-and-retraction-review.md)).
- Online checks: identifiers and citations are looked up in their registries on every data pull request, failing closed; excerpts only from CC BY or CC0 papers ([ADR 0007](docs/decisions/0007-online-identifier-checks.md)), over requests-cache, urllib3 Retry and requests-ratelimiter ([ADR 0012](docs/decisions/0012-http-packages.md)).
- Atlases: mouse (Allen CCFv3 2017), human (Allen 3D 2020) and rat (Waxholm v4), pinned and read from BrainGlobe at build time; regions mapped to UBERON by UBERON's bridges ([ADR 0009](docs/decisions/0009-atlas-layer.md)).
- Allen mouse connectivity: region-level claims made at build time from wild-type amygdala injections, never committed or dumped ([ADR 0010](docs/decisions/0010-allen-connectivity.md)).
- Serving database: read-shaped tables in Supabase, rebuilt from the files on every merge to main, read-only to the public ([ADR 0008](docs/decisions/0008-serving-database.md)).

## Handoff (4 October 2026)

**Live at https://axonarium.com:** the mouse amygdala's outputs and inputs from the Allen Mouse Brain Connectivity Atlas (2,053 claims, 1,039 connections), shown in 3D and as a linked network (`/brain`), in a sortable table (`/explore`), region by region (`/regions`), through a read API (`/api/v1`, [api/README.md](api/README.md)) and through an MCP server for AI agents ([api/mcp](api/mcp/README.md)).

**Not done:**
- The minors deferred by the final review of #29–#42: the 3D and network views hide connections without a density (all current ones have one), and the online checks refuse cached answers from a host that failed earlier in the same run.
- 1.5 SCKAN waits on a schema decision (below).
- 4.1 SONATA export is on hold until there is more data.

**Surprises:**
- BrainGlobe labels the Allen mouse atlas "asr", but Allen's own data puts the right hemisphere at large z. The meshes follow Allen (ADR 0011).
- The Allen API reports failed queries as HTTP 200, so the caches drop any answer that doesn't validate (ADR 0012).
- Dependabot holds TypeScript and ESLint majors until typescript-eslint and eslint-config-next support them.

**Next step:** more data: the 2.2 literature corpus (the start of extraction), and SCKAN once its evidence class is decided. The SONATA export (4.1) follows once there is more to export.

## Waiting on the maintainer

- [ ] SCKAN (sprint 1.5): SCKAN records no method per statement, so its claims need either a new evidence class for curated knowledge bases (a schema change, graded below every experimental method) or per-paper extraction later. Its pinned simple export (`npo-simple-sckan-merged.ttl`, release sckan-2026-02-11) also has about 1,200 malformed IRIs; the full release files would be the input.

- [ ] Gold-set curation: the maintainer alone, or with a second curator?
- [ ] Whether visitors can suggest papers that have no matching claim yet.
- [ ] The remaining open decisions in [docs/plan.md](docs/plan.md), Part 1.
- [ ] A trademark search before announcing.
- [ ] Auto-renew for axonarium.org, which expires 2027-10-02.
- [ ] Requiring 2FA in the GitHub organization.
- [ ] A second organization owner.
- [ ] Claiming the PyPI project names (`axonarium`, and `axonarium-mcp` for the MCP server, which installs from GitHub for now).
- [ ] Rotating the Vercel token and the Supabase database password, which were pasted in chat, and setting the new values in the `production` environment, where only jobs on `main` can read them: `gh secret set VERCEL_TOKEN --env production --repo axonarium/axonarium` and `gh secret set SUPABASE_DB_URL --env production --repo axonarium/axonarium`. Then the repository-level `VERCEL_TOKEN` (readable by any workflow, pull requests included) gets deleted.
- [ ] Registering https://w3id.org/axonarium/ with w3id.org (a pull request to its registry).
- [ ] Asking the Allen Institute for written permission to redistribute region and connectivity data under CC BY 4.0 (ADR 0005).
- [ ] Asking BAMS's maintainers for permission to reuse its connection reports (ADR 0005).

## Setup

From plan Part 3.5:

| Step | State |
| --- | --- |
| Project email alias | Done: admin@axonarium.com |
| Domains | Done: axonarium.com and axonarium.org; https://axonarium.com serves the site |
| GitHub organization and repo | Done; a second owner is needed |
| Vercel | Done: team and project `axonarium`, deployed from GitHub Actions |
| Supabase | Not started; needed for the live API in Phase 3 |
| LLM API key with a spending cap | Not started; needed for sprint 0.6 |
| PyPI and npm | npm scope held; PyPI project name unclaimed |

## Metrics

None yet.
