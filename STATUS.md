# Status

Hand-maintained until the Steward role generates it (Phase 6). Last updated 4 October 2026 (second session).

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
| 0.5 Gold set ([#6](https://github.com/axonarium/axonarium/issues/6)) | Waiting on the maintainer, who curates it into `agents/evals/gold/v1/` |
| 0.6 Eval harness ([#7](https://github.com/axonarium/axonarium/issues/7)) | Built ahead of gold v1 ([#63](https://github.com/axonarium/axonarium/pull/63)); "two models scored" waits on gold v1 and an API key |
| 1.1 Licence audit | Done |
| 1.2 Atlas layer | Done |
| 1.3 Allen mouse connectivity | Done: 2,053 build-time claims (717 accepted), 1,039 connections, the amygdala's outputs and inputs |
| 1.4 BAMS rat adapter ([#11](https://github.com/axonarium/axonarium/issues/11)) | Blocked until BAMS grants permission ([ADR 0005](docs/decisions/0005-source-reuse-terms.md)) |
| 1.5 SCKAN adapter ([#12](https://github.com/axonarium/axonarium/issues/12)) | Moved to Phase 7a, the vagal gut–brain module (maintainer, 4 October 2026) |
| 1.6 Reconciliation report ([#13](https://github.com/axonarium/axonarium/issues/13)) | Done ([#58](https://github.com/axonarium/axonarium/pull/58)): Allen and the literature; CI publishes the report with every run |
| 2.1 Amygdala inventory ([#59](https://github.com/axonarium/axonarium/issues/59)) | Drafted ([#60](https://github.com/axonarium/axonarium/pull/60)): 26 neuron types and the region naming traps; its open questions wait on the maintainer |
| 2.2 Literature corpus ([#61](https://github.com/axonarium/axonarium/issues/61)) | Done ([#62](https://github.com/axonarium/axonarium/pull/62)): the first Scout run's 2,079 papers are in `corpus/manifest.csv` ([#68](https://github.com/axonarium/axonarium/pull/68)) |
| 2.3–2.6 Extraction, verification, audit, homology | Not started: extraction waits on 0.6 and 2.2 |
| 3.1 Read API | Done: `/api/v1` with an OpenAPI 3.1 contract and reuse terms on every claim ([ADR 0013](docs/decisions/0013-read-api.md)) |
| 3.2 Release job ([#55](https://github.com/axonarium/axonarium/issues/55)) | Built ([#56](https://github.com/axonarium/axonarium/pull/56)); "a test release gets a DOI" needs Zenodo switched on for the repository |
| 3.3 Explorer v1 | Done: site shell, 3D brain, network view, region pages, and the static fallback ([#57](https://github.com/axonarium/axonarium/pull/57)) |
| 3.4 MCP server | Done: `api/mcp`, four read-only tools over the API ([ADR 0014](docs/decisions/0014-mcp-server.md)) |
| 3.5 Visual design pass | Not started; needs the maintainer's eye |
| 4.1 SONATA export ([#50](https://github.com/axonarium/axonarium/issues/50)) | On hold until there is more data (maintainer, 4 October 2026); its design starts from scratch then |
| C.1 Inbox and identifier vetting ([#64](https://github.com/axonarium/axonarium/issues/64)) | Done ([#65](https://github.com/axonarium/axonarium/pull/65)): the inbox table, closed to the public API, and identifier vetting |
| C.2 Allowlist ([#14](https://github.com/axonarium/axonarium/issues/14)) | Done ([#54](https://github.com/axonarium/axonarium/pull/54)) |
| C.3 Evidence buttons ([#72](https://github.com/axonarium/axonarium/issues/72)) | Built ([#73](https://github.com/axonarium/axonarium/pull/73)): Supports and Contradicts on each claim page, with Turnstile and rate limits ([ADR 0024](docs/decisions/0024-evidence-buttons.md)). Hidden until the maintainer sets the keys |
| C.4 Triage | Not started: waits on 2.4 |
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
- Allen mouse connectivity: region-level claims made at build time from wild-type amygdala injections, never committed or dumped ([ADR 0010](docs/decisions/0010-allen-connectivity.md)).
- Serving database: read-shaped tables in Supabase, rebuilt from the files on every merge to main, read-only to the public ([ADR 0008](docs/decisions/0008-serving-database.md)).
- SCKAN moves to Phase 7a, the gut–brain module; the reconciliation report proceeds with Allen and the literature (maintainer, 4 October 2026).
- The eval harness is built ahead of gold v1 and scores models from several providers, so extractor and verifier can come from different families (maintainer, 4 October 2026; [ADR 0020](docs/decisions/0020-eval-harness.md)).
- The amygdala inventory is drafted by an agent for the maintainer's review: neuron types and synonyms authored by the project, regions referenced by ID only (maintainer, 4 October 2026).
- Agents merge pull requests only when the maintainer, in that agent's own session, tells them to, once CI passes ([ADR 0022](docs/decisions/0022-agents-merge-when-told.md)).
- Hidden text: every paper passes a screen before a model reads it. Invisible characters and hidden markup are stripped, and Protect AI's prompt-injection classifier (LLM Guard's default, PhantomLint's suspicion test) scores each paragraph. A flagged paper never reaches a model ([ADR 0023](docs/decisions/0023-hidden-text-screen.md)).
- Evidence buttons: Turnstile is checked on the server, and the rate limits (5 an hour and 20 a day per submitter, 500 a day overall) are enforced in the database by a keyed hash of the address, cleared after a day ([ADR 0024](docs/decisions/0024-evidence-buttons.md)).

## Handoff (4 October 2026, second session)

**Live at https://axonarium.com:** the mouse amygdala's outputs and inputs from the Allen Mouse Brain Connectivity Atlas, shown in 3D and as a network (`/brain`), in a table (`/explore`), region by region (`/regions`), through the read API (`/api/v1`) and through the MCP server. The site now answers from a snapshot of the database when Supabase can't.

**Done and merged**, each with CI green on main and a successful deploy after it:
- [#53](https://github.com/axonarium/axonarium/pull/53): the two minors left from the last review. Connections without a density now show in the 3D and network views, and cached answers are still used when a host goes down.
- [#54](https://github.com/axonarium/axonarium/pull/54) C.2: the allowlist. Source records gain a registry-derived `kind` (schema 0.4.0).
- [#56](https://github.com/axonarium/axonarium/pull/56) 3.2: the Release workflow (dumps plus Zenodo).
- [#57](https://github.com/axonarium/axonarium/pull/57) 3.3: the site answers from a snapshot of the database when Supabase can't.
- [#58](https://github.com/axonarium/axonarium/pull/58) 1.6: the reconciliation report, in every CI run's summary.
- [#60](https://github.com/axonarium/axonarium/pull/60) 2.1: the amygdala inventory draft.
- [#62](https://github.com/axonarium/axonarium/pull/62) 2.2: the literature scout and the Scout workflow. Its first run found 2,079 papers: [#68](https://github.com/axonarium/axonarium/pull/68), after [#69](https://github.com/axonarium/axonarium/pull/69) let the manifest grow past pre-commit's 500 KB limit.
- [#63](https://github.com/axonarium/axonarium/pull/63) 0.6: the eval harness. It works with any provider, plus a first extractor prompt.
- [#65](https://github.com/axonarium/axonarium/pull/65) C.1: the community inbox and identifier vetting.
- [#67](https://github.com/axonarium/axonarium/pull/67): agents merge the pull requests the maintainer names (ADR 0022).

**Prepared for the maintainer, outside the repository:** the w3id.org registration (`ids/axonarium/.htaccess`, passing the registry's checker and tested on a local Apache), permission emails to the Allen Institute and BAMS, and a preliminary trademark search (no "Axonarium" mark found on the web; the official databases are still to search).

**Not done:** the gold set (0.5); extraction, verification and audit (2.3–2.5); homology claims (2.6); the visual design pass (3.5); triage (C.4); BAMS (blocked); SCKAN (Phase 7a); SONATA (on hold).

**Surprises:**
- This session's sandbox couldn't reach Crossref, NCBI, OLS, Europe PMC or the Allen API. Every identifier in the inventory and the extractor prompt was checked against UBERON's, the Cell Ontology's and BICAN's MBA sources from GitHub instead. CI's online checks looked them up again.
- Allen's "BLA" is the whole basolateral nucleus, while Paxinos's "BLA" is its anterior part. Many behavioural papers mean the whole basolateral complex. The extractor's normaliser must handle all three (spec for 2.1).
- The plan's anonymous insert into the inbox would have let anyone bypass Turnstile with the public key, so the inbox is closed to the public API instead (ADR 0021).
- The first manifest (713 KB) tripped pre-commit's 500 KB limit for added files; the manifest is now exempt ([#69](https://github.com/axonarium/axonarium/pull/69)).
- The first corpus holds 188 preprints and one retraction notice. It's a reading queue, so they stay; the allowlist and retraction checks apply when claims are extracted.

**Next step:** enable Zenodo and run **Release**, and curate gold v1. With gold v1 and an API key, score two models (0.6) and start extraction (2.3) on the corpus's open-access papers.

## Waiting on the maintainer

- [ ] Gold-set curation (sprint 0.5): the maintainer alone, or with a second curator? Its format is in `agents/evals/README.md`.
- [ ] An LLM API key with a spending cap (`ANTHROPIC_API_KEY`, and `OPENAI_API_KEY` for a second model family), for the eval harness and extraction.
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
| LLM API key with a spending cap | Not started; needed to score models (0.6) and to extract (2.3) |
| PyPI and npm | npm scope held; PyPI project name unclaimed |

## Metrics

None yet.
