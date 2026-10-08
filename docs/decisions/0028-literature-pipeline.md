---
status: accepted
date: 2026-10-08
decision-makers: Tyler Banks
consulted: Claude (sprints 2.2a–2.4)
---

# The literature pipeline: triage, extraction and verification on the Batch API

## Context and Problem Statement

Phase 2 fills the graph from the literature: Scout's corpus holds 2,079 papers (sprint 2.2), of which Europe PMC holds the full text of 874. The plan's agent roles say who does what (Extractor, Verifier), and the eval harness (ADR 0020) and the hidden-text screen (ADR 0023) exist. The project has no funding, but it has $1,000 of promotional API credits. How do papers become claims cheaply, repeatably and safely, and what do the claims mean before the gold set (sprint 0.5) can measure the models?

## Considered Options

* One Python pipeline, `python -m pipeline triage|extract|verify`, on the Batch API, run from a manual GitHub workflow or locally with a key
* Extraction inside Claude Code sessions on the maintainer's subscription
* Live (non-batch) API calls from a scheduled workflow

## Decision Outcome

Chosen option: "one pipeline on the Batch API". The Batch API halves every token's price and suits work that can wait an hour. A pipeline in code runs the same way on a laptop and in CI, and its prompts and models are the ones the eval harness scores. Claude Code sessions stay possible later, but their output would come from a different setup than the one the evals measure. Live calls cost twice as much for no gain here.

* **Three steps,** each a subcommand, each reading and writing files in the repository:
  1. **Triage** (sprint 2.2a): each paper's abstract, fetched from Europe PMC at run time and never stored, gets one question: does this paper's own data test a connection? The verdict goes in `corpus/triage.csv`.
  2. **Extraction** (sprint 2.3): for papers triaged in and open access with full text (Europe PMC serves full text only for its open-access subset), the pipeline sends the parts that hold claims: the abstract, results, methods and figure and table captions, without the introduction, discussion, acknowledgements or references. The text passes the hidden-text screen first; a flagged paper is never sent. Draft claims become claim files in `data/claims/amygdala/`, and `corpus/extracted.csv` records what each paper gave.
  3. **Verification** (sprint 2.4): a separate prompt reads the same text and each claim drafted from it, without the extractor's reasoning, and gives a verdict (agree, disagree or unsure) per claim. The verdict goes in the claim's `verification`.
* **Strength and numbers:** a claim also carries the strength the paper itself grades (weak, moderate or strong) and the numbers it reports: connection probability, the fraction of labelled neurons, synapse counts and conduction delay, each with its spread and sample size when given. Fractions are 0 to 1; a number outside its quantity's range is left out and reported. A paper's projection density stays in the paraphrase: papers normalise it each in their own way, so it can't share a scale with Allen's, which sets the brain view's arc widths. The verifier checks the numbers too.
* **Region names:** the extractor gets a lexicon of the pinned atlases' regions, built at run time from the atlases the build loads (Allen names are never committed; ADR 0005). Any region ID a draft claim gives that isn't in the lexicon drops that claim, and the run reports it.
* **Every extracted claim is `proposed`** until Gate 2, whatever the verifier says. Gate 2 needs the gold set and an audit's precision. After it, the maintainer decides whether verified claims become `accepted`. The site draws proposed claims dashed, as it does Allen's.
* **Models:** each step takes a `provider:model` and an effort. The default is `claude-opus-5-5` (triage at low effort, extraction at high, verification at medium). The evals decide when a cheaper model or another family is good enough. Claude Opus 5.5's bio classifier refuses some papers on viral tracers (rabies, pseudorabies, herpes simplex) and on drugs, 110 of 2,079 abstracts (5%) at triage. The Batch API takes no server-side fallbacks, so the pipeline sends refused requests to Claude Opus 5, which refuses far fewer (it answered 89 of the 91 it was sent at triage), in the same run (`--fallback`; `none` turns it off). Each claim and ledger row names the model that actually answered, and the run's cost counts both. With an OpenAI key, the verifier can come from another model family, as the plan prefers.
* **Where it runs:** the **Literature** workflow, started by hand from the Actions tab on `main`, with a step, a paper limit and a model. Its key is the `ANTHROPIC_API_KEY` secret of a `models` environment that only `main` may use, so pull requests never see it. It pushes a `literature/<step>-<date>` branch, and the maintainer, or an agent told to, opens the pull request: one opened with the workflow's own token wouldn't run CI. Locally, the same commands run with a key in the environment.
* **Spending:** each run has a paper limit. Each run reports its tokens and their cost at list and batch prices, and the Console's spend limit is the hard cap. The ledgers (`corpus/triage.csv`, `corpus/extracted.csv`, `corpus/verified.csv`) mean each step reads a paper once. A new version of a prompt doesn't read finished papers again; that takes an explicit `--redo` (named papers, `older` or `all`). A paper whose answers keep failing is set aside after two reads. A run refuses to start while another branch holds results not yet merged, and a batch still running when a run stops waiting is collected later by its ID (`--collect`), not sent again.
* **Security:** paper text is untrusted. It passes the screen, models get no tools, and their output is schema-checked data that CI then validates like any claim file. The workflow never runs on pull requests.

### Consequences

* Good, because the backlog costs little: about 2,000 abstracts and 874 full texts at batch prices fit well inside the credits, with room for re-runs as prompts improve.
* Good, because a run on a laptop and a run in CI are the same code, and the ledgers let either pick up where the other stopped.
* Bad, because until the gold set exists, nobody knows how good the claims are. Marking them all `proposed` keeps that visible.
* Bad, because a batch can take up to a day. Small trial runs can use `--now` (live calls at full price).
* Neutral: papers without open full text (most of those before 2010) wait for other routes, such as BAMS or WhiteText. That includes author manuscripts Europe PMC holds but won't serve: of the 705 papers triaged in with full text in Europe PMC, 358 are open access.
