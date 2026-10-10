# Status

Hand-maintained until the Steward role generates it (Phase 6). Last updated 10 October 2026.

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
| 2.2a Abstract triage ([#79](https://github.com/axonarium/axonarium/issues/79)), 2.3 extraction ([#80](https://github.com/axonarium/axonarium/issues/80)), 2.4 verification ([#81](https://github.com/axonarium/axonarium/issues/81)) | Done for the open-access corpus, from the **Literature** workflow ([ADR 0028](docs/decisions/0028-literature-pipeline.md)). Triage: of 2,079 papers, 1,608 in, 468 out, 3 set aside after two refusals. Extraction read all 358 open-access papers triaged in that have a PMC ID: 308 gave 3,272 claims (2,558 mouse, 714 rat), 9 gave none, 30 were screened out, and 11 are set aside because Europe PMC fails on them. Every claim has a verdict: 3,180 agree, 58 disagree, 34 unsure; the disagreements and doubts wait in [#116](https://github.com/axonarium/axonarium/issues/116). Papers without open-access full text are left out, since Europe PMC won't serve it. Claims stay proposed until Gate 2 |
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
- The literature pipeline reads each paper once per step unless asked, sends Claude Opus 5.5's refusals to Claude Opus 5 in the same run, and extracts only open-access papers, the only full text Europe PMC serves ([ADR 0028](docs/decisions/0028-literature-pipeline.md)).

## Handoff (10 October 2026, fifth session)

**Live at https://axonarium.com:** the mouse amygdala's outputs and inputs from the Allen Mouse Brain Connectivity Atlas, from wild-type and Cre-line injections, and 3,272 claims from 308 papers, each with its verifier's verdict. They are shown in 3D and as a network (`/brain`), in a table (`/explore`), region by region (`/regions`), paper by paper (`/sources`), through the read API (`/api/v1`) and through the MCP server.

**Done and merged this session**, each with CI green:
- Earlier in the session: the numbers extraction records ([#101](https://github.com/axonarium/axonarium/pull/101)), the whole corpus triaged ([#102](https://github.com/axonarium/axonarium/pull/102), [#103](https://github.com/axonarium/axonarium/pull/103), [#106](https://github.com/axonarium/axonarium/pull/106)), refusals sent to Claude Opus 5 ([#105](https://github.com/axonarium/axonarium/pull/105)), the first claims from papers ([#107](https://github.com/axonarium/axonarium/pull/107)), and extraction from open-access papers only ([#108](https://github.com/axonarium/axonarium/pull/108)).
- [#113](https://github.com/axonarium/axonarium/pull/113), [#115](https://github.com/axonarium/axonarium/pull/115), [#117](https://github.com/axonarium/axonarium/pull/117), [#119](https://github.com/axonarium/axonarium/pull/119), [#121](https://github.com/axonarium/axonarium/pull/121), [#122](https://github.com/axonarium/axonarium/pull/122), [#123](https://github.com/axonarium/axonarium/pull/123), [#126](https://github.com/axonarium/axonarium/pull/126), [#129](https://github.com/axonarium/axonarium/pull/129), [#130](https://github.com/axonarium/axonarium/pull/130), [#132](https://github.com/axonarium/axonarium/pull/132), [#133](https://github.com/axonarium/axonarium/pull/133), [#135](https://github.com/axonarium/axonarium/pull/135): the whole open-access backlog, in runs of about 50 papers. 3,272 claims from 308 papers, all verified: 3,180 agree, 58 disagree, 34 unsure. Extraction cost about $0.20–0.25 a paper and verification about $0.05–0.08.
- [#128](https://github.com/axonarium/axonarium/pull/128): a run's results are pushed on main as it is when the run ends, after GitHub refused a branch built on an older main; `--collect-fallback` collects a run's fallback batch too, so refusals aren't paid for twice.
- [#134](https://github.com/axonarium/axonarium/pull/134): the peer review eLife prints with a paper (decision letters, authors' responses) is pruned before the screen and the model; the extractor had been reading it, and the screen setting papers aside for it.
- [#110](https://github.com/axonarium/axonarium/pull/110): the Literature workflow fits its batch waits into the job's six hours (`--wait`), so a slow batch is collected later instead of lost.
- [#111](https://github.com/axonarium/axonarium/pull/111), [#112](https://github.com/axonarium/axonarium/pull/112): `--collect latest` finds the step's own newest batch when a run's log is gone.
- [#127](https://github.com/axonarium/axonarium/pull/127): `extract-and-verify` pushes the extracted claims whatever happens to verification.
- [#118](https://github.com/axonarium/axonarium/pull/118), [#120](https://github.com/axonarium/axonarium/pull/120): each paper that couldn't be read says why, and a paper Europe PMC answers with a server error twice is set aside.
- [#124](https://github.com/axonarium/axonarium/pull/124): a conduction delay of zero is left out.
- [#125](https://github.com/axonarium/axonarium/pull/125): the guard against running over waiting results counts only the ledger rows a branch wrote, so a stale code branch no longer blocks a run.
- [#114](https://github.com/axonarium/axonarium/pull/114): buttons no longer fade in when they are enabled, which made the contrast check fail now and then.
- [#116](https://github.com/axonarium/axonarium/issues/116): the review queue for claims the verifier disagreed with or was unsure of.

**Not done:**
- 4 open-access preprints have only a Europe PMC preprint ID, no PMC ID, so extraction skips them; and the 30 papers the screen set aside wait on question 3 in #116.
- The review queue ([#116](https://github.com/axonarium/axonarium/issues/116)) and its five questions. A proposed `extract@0.4.0` waits on the answers.
- Gold v1 (0.5), and with it the harness scores (0.6, 0.6a #92) and the audit (2.5).
- 1.8 and 1.9: their files' formats need checking from a machine that can reach figshare and Janelia.
- The look of 3.5; homology (2.6); C.4; BAMS (blocked); SCKAN (Phase 7a); SONATA (on hold).

**Surprises:**
- Opus 5.5 refused about half the full texts at extraction (152 of the 317 papers sent went to Opus 5), against 5% of abstracts at triage.
- The verifier's disagreements are mostly real catches: antidromic spikes read as the wrong direction, axons labelled by a retrograde virus recorded as anterograde, chemogenetics recorded as optogenetics, other numbers read as connection probabilities, feed-forward inhibition read as an inhibitory input, and targets taken from a figure's list of abbreviations.
- Several of its doubts are about naming, not the paper: mPFC, the superior colliculus and the amygdalostriatal transition area have no single Allen region.
- The hidden-text screen set aside about 1 in 11 fetched papers. The ones checked were false positives: primer sequences, protocol boilerplate, figure titles.
- Europe PMC answers some open-access papers with a server error every time, six *Nature* papers among them.
- The verifier missed one claim the review caught: response latencies of 129 and 172 ms recorded as conduction delays (#116). A plausibility bound in code would catch that kind.

**Next step:** the backlog is done. The maintainer's answers on #116 decide `extract@0.4.0`, and then whether to read the affected papers again. New papers come from a Scout run, then `triage` and `extract-and-verify`.

## Waiting on the maintainer

- [ ] The review queue ([#116](https://github.com/axonarium/axonarium/issues/116)): retract or correct the claims the verifier disagreed with, and answer its five questions on region naming, the screen and evidence classes.
- [ ] The look review for sprint 3.5 ([#74](https://github.com/axonarium/axonarium/issues/74)): design tokens, motion, and whether phones get a lighter home preview (it costs a phone 0.3–0.5 s of blocking time; ADR 0025). Then #74 can close.
- [ ] Gap mode's rule (ADR 0027): whether suggestions from neighbouring subdivisions are the research prompts you want. Also whether routes and gaps should join the read API and the MCP server: two of the plan's acceptance questions ask for them.
- [ ] Gold-set curation (sprint 0.5): the maintainer alone, or with a second curator? Its format is in `agents/evals/README.md`.
- [ ] Whether extraction should record a population's genetic handle (a Cre line or marker, such as Prkcd-Cre) in its own field. For now the paper's own wording is kept with each claim (`extract.subject_name`, `extract.object_name`).
- [ ] Optionally, an `OPENAI_API_KEY` in the `models` environment, so the verifier can come from a second model family (ADR 0028).
- [ ] Deleting the branch `claude/probe-data`, which merged pull requests' branches no longer leave behind; agents can't delete branches.
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
