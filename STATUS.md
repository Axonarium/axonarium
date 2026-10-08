# Status

Hand-maintained until the Steward role generates it (Phase 6). Last updated 8 October 2026.

## Phase

Phase 0, Foundations: in progress. Gate 0 passes when a full rebuild from empty passes, the gold set is frozen and the eval harness runs.

## Sprints

Sprint cards are [GitHub issues labelled `sprint`](https://github.com/axonarium/axonarium/issues?q=is%3Aissue%20label%3Asprint).

| Sprint | State |
| --- | --- |
| 0.1 Repo scaffold | Done |
| 0.2 Schema v0.1 in LinkML | Done |
| 0.3 Validation CI, 0.3b online identifier checks, 0.3c retraction status without a DOI, 0.3d standard HTTP packages | Done |
| 0.4 Rebuild pipeline | Done |
| 0.5 Gold set ([#6](https://github.com/axonarium/axonarium/issues/6)) | Waiting on the maintainer, who curates it into `agents/evals/gold/v1/`, with the tool from 0.5a |
| 0.5a Gold curation tool ([#82](https://github.com/axonarium/axonarium/issues/82)) | Built: `cd agents && uv run python -m curate` serves a local page with a paper beside a claim form and region search, and saves drafts in the gold format to `.cache/gold-drafts/` |
| 0.6 Eval harness ([#7](https://github.com/axonarium/axonarium/issues/7)) | Built ahead of gold v1 ([#63](https://github.com/axonarium/axonarium/pull/63)); "two models scored" waits on gold v1 |
| 0.6a Harness parity ([#92](https://github.com/axonarium/axonarium/issues/92)) | Next: the harness gives the extractor the lexicon and pruned text the pipeline does, so gold scores predict pipeline runs; a human-owned path, so it waits on the maintainer's review |
| 1.1 Licence audit | Done |
| 1.2 Atlas layer | Done |
| 1.3 Allen mouse connectivity | Done: 2,053 build-time claims (717 accepted), 1,039 connections, the amygdala's outputs and inputs |
| 1.4 BAMS rat adapter ([#11](https://github.com/axonarium/axonarium/issues/11)) | Blocked until BAMS grants permission ([ADR 0005](docs/decisions/0005-source-reuse-terms.md)) |
| 1.5 SCKAN adapter ([#12](https://github.com/axonarium/axonarium/issues/12)) | Moved to Phase 7a, the vagal gut–brain module (maintainer, 4 October 2026) |
| 1.6 Reconciliation report ([#13](https://github.com/axonarium/axonarium/issues/13)) | Done ([#58](https://github.com/axonarium/axonarium/pull/58)): Allen and the literature; CI publishes the report with every run |
| 1.7 Allen Cre-line experiments ([#83](https://github.com/axonarium/axonarium/issues/83)) | Done: region-level claims from Cre-line experiments too, each recording its line ([ADR 0029](docs/decisions/0029-allen-cre-lines.md)) |
| 1.8 Single-neuron reconstructions ([#84](https://github.com/axonarium/axonarium/issues/84)), 1.9 WhiteText statements ([#85](https://github.com/axonarium/axonarium/issues/85)) | Planned: more data without model costs. Both need their files' real formats checked first (MouseLight's export, WhiteText's XML); the agents' sandbox can't reach figshare or Janelia yet |
| 2.1 Amygdala inventory ([#59](https://github.com/axonarium/axonarium/issues/59)) | Drafted ([#60](https://github.com/axonarium/axonarium/pull/60)): 26 neuron types and the region naming traps; its open questions wait on the maintainer |
| 2.2 Literature corpus ([#61](https://github.com/axonarium/axonarium/issues/61)) | Done ([#62](https://github.com/axonarium/axonarium/pull/62)): the first Scout run's 2,079 papers are in `corpus/manifest.csv` ([#68](https://github.com/axonarium/axonarium/pull/68)) |
| 2.2a Abstract triage ([#79](https://github.com/axonarium/axonarium/issues/79)), 2.3 extraction ([#80](https://github.com/axonarium/axonarium/issues/80)), 2.4 verification ([#81](https://github.com/axonarium/axonarium/issues/81)) | Built ([#88](https://github.com/axonarium/axonarium/pull/88), [#90](https://github.com/axonarium/axonarium/pull/90), [#91](https://github.com/axonarium/axonarium/pull/91)): one pipeline on the Batch API, run from the **Literature** workflow or locally ([ADR 0028](docs/decisions/0028-literature-pipeline.md)). The first real run waits on the `models` key. Claims stay proposed until Gate 2 |
| 2.5 Audit, 2.6 homology | Not started: the audit needs gold v1 and extracted claims |
| 3.1 Read API | Done: `/api/v1` with an OpenAPI 3.1 contract and reuse terms on every claim ([ADR 0013](docs/decisions/0013-read-api.md)) |
| 3.2 Release job ([#55](https://github.com/axonarium/axonarium/issues/55)) | Built ([#56](https://github.com/axonarium/axonarium/pull/56)); "a test release gets a DOI" needs Zenodo switched on for the repository |
| 3.3 Explorer v1 | Done: site shell, 3D brain, network view, region pages, and the static fallback ([#57](https://github.com/axonarium/axonarium/pull/57)) |
| 3.4 MCP server | Done: `api/mcp`, four read-only tools over the API ([ADR 0014](docs/decisions/0014-mcp-server.md)) |
| 3.5 Visual design pass ([#74](https://github.com/axonarium/axonarium/issues/74)) | Accessibility and performance budgets in CI ([#75](https://github.com/axonarium/axonarium/pull/75), [ADR 0025](docs/decisions/0025-site-budgets.md)). Figure export ([#76](https://github.com/axonarium/axonarium/pull/76)): either brain view as a PNG, the network as an SVG, each with a title, legend and the Allen citation. Path finder: a route between two regions, drawn hop by hop with each hop's citations ([ADR 0026](docs/decisions/0026-routes-in-the-browser.md)). Gap mode: amygdala regions no claim reports outputs for, drawn to the targets their neighbours project to, as research prompts ([ADR 0027](docs/decisions/0027-gap-mode.md)). The look (tokens, motion) is next and needs the maintainer's eye |
| 4.1 SONATA export ([#50](https://github.com/axonarium/axonarium/issues/50)) | On hold until there is more data (maintainer, 4 October 2026); its design starts from scratch then |
| C.1 Inbox and identifier vetting ([#64](https://github.com/axonarium/axonarium/issues/64)) | Done ([#65](https://github.com/axonarium/axonarium/pull/65)): the inbox table, closed to the public API, and identifier vetting |
| C.2 Allowlist ([#14](https://github.com/axonarium/axonarium/issues/14)) | Done ([#54](https://github.com/axonarium/axonarium/pull/54)) |
| C.3 Evidence buttons ([#72](https://github.com/axonarium/axonarium/issues/72)) | Built ([#73](https://github.com/axonarium/axonarium/pull/73)): Supports and Contradicts on each claim page, with Turnstile and rate limits ([ADR 0024](docs/decisions/0024-evidence-buttons.md)). Hidden until the maintainer sets the keys |
| C.4 Triage | Not started: waits on 2.4 |
| 6.1 Autopilot ([#86](https://github.com/axonarium/axonarium/issues/86)) | Planned: weekly Scout, triage, extraction and verification with a spend cap and a kill switch |
| C.5 Hidden-text screen ([#70](https://github.com/axonarium/axonarium/issues/70)) | Done ([#71](https://github.com/axonarium/axonarium/pull/71)): every paper is screened before a model reads it, and a flagged one never is ([ADR 0023](docs/decisions/0023-hidden-text-screen.md)) |

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
- Allen mouse connectivity: region-level claims made at build time from wild-type and Cre-line injections, never committed or dumped; a Cre-line claim records its line ([ADR 0010](docs/decisions/0010-allen-connectivity.md), [ADR 0029](docs/decisions/0029-allen-cre-lines.md)).
- Serving database: read-shaped tables in Supabase, rebuilt from the files on every merge to main, read-only to the public ([ADR 0008](docs/decisions/0008-serving-database.md)).
- SCKAN moves to Phase 7a, the gut–brain module; the reconciliation report proceeds with Allen and the literature (maintainer, 4 October 2026).
- The eval harness is built ahead of gold v1 and scores models from several providers, so extractor and verifier can come from different families (maintainer, 4 October 2026; [ADR 0020](docs/decisions/0020-eval-harness.md)).
- The amygdala inventory is drafted by an agent for the maintainer's review: neuron types and synonyms authored by the project, regions referenced by ID only (maintainer, 4 October 2026).
- Agents merge pull requests only when the maintainer, in that agent's own session, tells them to, once CI passes ([ADR 0022](docs/decisions/0022-agents-merge-when-told.md)).
- Hidden text: every paper passes a screen before a model reads it. Invisible characters and hidden markup are stripped, and Protect AI's prompt-injection classifier (LLM Guard's default, PhantomLint's suspicion test) scores each paragraph. A flagged paper never reaches a model ([ADR 0023](docs/decisions/0023-hidden-text-screen.md)).
- Evidence buttons: Turnstile is checked on the server, and the rate limits (5 an hour and 20 a day per submitter, 500 a day overall) are enforced in the database by a keyed hash of the address, cleared after a day ([ADR 0024](docs/decisions/0024-evidence-buttons.md)).
- Site budgets: axe-core (WCAG 2.1 AA, no violations) on every page type at phone and desktop sizes, and Lighthouse on a mid-range phone, in CI on real data ([ADR 0025](docs/decisions/0025-site-budgets.md)).
- Routes are found in the browser over the connections the brain page loads: the fewest hops, then the strongest weakest hop ([ADR 0026](docs/decisions/0026-routes-in-the-browser.md)).
- Gap mode: the build suggests outputs for amygdala regions no claim reports outputs for, from their neighbours' targets. Species gaps join once rat and homology claims exist ([ADR 0027](docs/decisions/0027-gap-mode.md)).
- The literature pipeline: triage, extraction and verification on the Batch API, run by hand from GitHub Actions or locally, paid from $1,000 of promotional API credits; extracted claims stay proposed until Gate 2 ([ADR 0028](docs/decisions/0028-literature-pipeline.md)).

## Handoff (8 October 2026, fourth session)

**Live at https://axonarium.com:** the mouse amygdala's outputs and inputs from the Allen Mouse Brain Connectivity Atlas, now from Cre-line injections too. They are shown in 3D and as a network (`/brain`), in a table (`/explore`), region by region (`/regions`), through the read API (`/api/v1`) and through the MCP server. In `/brain`, figures download as PNG and SVG, the path finder draws a route hop by hop with its citations, and gap mode suggests untested outputs.

**Done and merged this session**, each with CI green:
- [#76](https://github.com/axonarium/axonarium/pull/76), [#77](https://github.com/axonarium/axonarium/pull/77), [#78](https://github.com/axonarium/axonarium/pull/78) 3.5: figure export, the path finder and gap mode.
- [#87](https://github.com/axonarium/axonarium/pull/87): the literature pipeline's plan (ADR 0028) and sprint cards #79–#86.
- [#88](https://github.com/axonarium/axonarium/pull/88) 2.2a, [#90](https://github.com/axonarium/axonarium/pull/90) 2.3, [#91](https://github.com/axonarium/axonarium/pull/91) 2.4: triage, extraction and verification, run by `python -m pipeline` and the **Literature** workflow.
- [#89](https://github.com/axonarium/axonarium/pull/89) 1.7: Allen's Cre-line experiments (ADR 0029).
- [#93](https://github.com/axonarium/axonarium/pull/93) 0.5a: the gold curation tool (`python -m curate`).
- [#94](https://github.com/axonarium/axonarium/pull/94), [#96](https://github.com/axonarium/axonarium/pull/96): the pipeline never pays for a paper twice.
  - A batch that outlives a run's wait is collected later (`--collect`).
  - Each step reads a paper once, whatever the prompt version, unless asked (`--redo`).
  - A failing paper is set aside after two reads.
  - A run refuses to start while another branch holds its results.
  - Verification has its own ledger, `corpus/verified.csv`.
- [#97](https://github.com/axonarium/axonarium/pull/97), [#98](https://github.com/axonarium/axonarium/pull/98): the site is ready for claims from papers.
  - Rat claims' UBERON terms and neuron types are shown by name.
  - Each claim says who made it and what the independent check said.
  - Sources has a page per paper with every claim drawn from it, and an index (`/sources`).
- [#99](https://github.com/axonarium/axonarium/pull/99): the **Literature** workflow's `extract-and-verify` step, so claims arrive already checked, in one pull request.
- [#95](https://github.com/axonarium/axonarium/pull/95): a timing flake in the route test's accessibility check.

**Not done:**
- No model has been called yet: the first real run waits on the `models` key (below).
- Gold v1 (0.5), and with it the harness scores (0.6, 0.6a #92) and the audit (2.5).
- 1.8 and 1.9: their files' formats need checking from a machine that can reach figshare and Janelia.
- The look of 3.5; homology (2.6); C.4; BAMS (blocked); SCKAN (Phase 7a); SONATA (on hold).

**Surprises:**
- The eval harness doesn't give the extractor the region lexicon or the pruned text, so its scores wouldn't match pipeline runs (#92).
- This session's sandbox couldn't reach the Anthropic API, Europe PMC, the Allen API, Hugging Face, figshare or Janelia. The pipeline was tested with replayed answers and a synthetic article, so the first real run is its real test.

**Next step:** once the key is in place, run **Literature** with step `triage` and limit 20, and read the report: the verdicts, the tokens and the cost. If they look right, triage the rest; then run `extract-and-verify` on a few papers. Each run pushes a `literature/…` branch to open a pull request from; once it merges, the deploy puts its claims on the site, under each connection and on each paper's page in Sources. Rough cost at batch prices for the open-access backlog (about 2,000 abstracts, then the few hundred open papers triage keeps): $100–200 in all. This is an estimate; each run's report gives the real figure.

## Waiting on the maintainer

- [ ] The look review for sprint 3.5 ([#74](https://github.com/axonarium/axonarium/issues/74)): design tokens, motion, and whether phones get a lighter home preview (it costs a phone 0.3–0.5 s of blocking time; ADR 0025). Then #74 can close.
- [ ] Gap mode's rule (ADR 0027): whether suggestions from neighbouring subdivisions are the research prompts you want. Also whether routes and gaps should join the read API and the MCP server: two of the plan's acceptance questions ask for them.
- [ ] Gold-set curation (sprint 0.5): the maintainer alone, or with a second curator? Its format is in `agents/evals/README.md`.
- [ ] The pipeline's key (ADR 0028): in the Anthropic Console, create an API key in the workspace holding the credits and set a monthly spend limit there. Then in GitHub, under Settings → Environments, create an environment named `models`, limit it to the `main` branch, and add the key as the secret `ANTHROPIC_API_KEY`. An `OPENAI_API_KEY` there too would let the verifier come from a second model family.
- [ ] Zenodo: switch on `axonarium/axonarium` in Zenodo's GitHub settings, run **Release**, then add the concept DOI to `README.md`, `CITATION.cff` and `SUCCESSION.md` (ADR 0016). Also whether `CITATION.cff` should list CC BY 4.0 beside Apache-2.0.
- [ ] Whether to annotate `corpus/` as CC0-1.0 in `REUSE.toml` (ADR 0019). Later Scout runs: run it from the Actions tab and open a pull request from the branch it pushes.
- [ ] The inventory draft's open questions (spec for 2.1): where the lexicon lives, whether neuron types cite papers, how Cre-line experiments map to them.
- [ ] Whether low-density Allen inputs, possibly fibres of passage, need a higher threshold (ADR 0010). The reconciliation report in CI's run summary gives the numbers.
- [ ] Opening submissions (sprint C.3, ADR 0024): create a Turnstile widget for axonarium.com in Cloudflare; set its site key as the GitHub variable `NEXT_PUBLIC_TURNSTILE_SITE_KEY` (production environment), and its secret key and Supabase's secret key as `TURNSTILE_SECRET_KEY` and `SUPABASE_SECRET_KEY` in Vercel (production, sensitive). Then send one paper from a phone. A dedicated database role instead of the secret key stays open (ADR 0021).
- [ ] Whether visitors can suggest papers that have no matching claim yet.
- [ ] The remaining open decisions in [docs/plan.md](docs/plan.md), Part 1.
- [ ] A trademark search before announcing: search the USPTO, WIPO and EUIPO databases for "axonarium" in classes 9, 41 and 42. The web search found none.
- [ ] Auto-renew for axonarium.org, which expires 2027-10-02.
- [ ] Requiring 2FA in the GitHub organization.
- [ ] A second organization owner.
- [ ] Claiming the PyPI project names (`axonarium`, and `axonarium-mcp` for the MCP server, which installs from GitHub for now).
- [ ] Rotating the Vercel token and the Supabase database password, which were pasted in chat, and setting the new values in the `production` environment, where only jobs on `main` can read them: `gh secret set VERCEL_TOKEN --env production --repo axonarium/axonarium` and `gh secret set SUPABASE_DB_URL --env production --repo axonarium/axonarium`. Then the repository-level `VERCEL_TOKEN` (readable by any workflow, pull requests included) gets deleted.
- [ ] Registering https://w3id.org/axonarium/ with w3id.org: a pull request adding `ids/axonarium/.htaccess` to perma-id/w3id.org from your fork (file prepared on 4 October 2026).
- [ ] Asking the Allen Institute (terms@alleninstitute.org) for written permission to redistribute region and connectivity data under CC BY 4.0 (ADR 0005); email drafted.
- [ ] Asking BAMS's maintainers for permission to reuse its connection reports (ADR 0005); email drafted, contact to confirm on BAMS's policy page.

## Setup

From plan Part 3.5:

| Step | State |
| --- | --- |
| Project email alias | Done: admin@axonarium.com |
| Domains | Done: axonarium.com and axonarium.org; https://axonarium.com serves the site |
| GitHub organization and repo | Done; a second owner is needed |
| Vercel | Done: team and project `axonarium`, deployed from GitHub Actions |
| Zenodo | Not started; needed for release DOIs (3.2) |
| Supabase | Done: the serving database, rebuilt by every deploy; the site falls back to a snapshot when it can't answer |
| LLM API key with a spending cap | $1,000 of promotional API credits (8 October 2026); the key goes in the `models` environment (ADR 0028) |
| PyPI and npm | npm scope held; PyPI project name unclaimed |

## Metrics

None yet.
