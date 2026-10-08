# Agents

The prompts that agents work from, the harness that decides which models may fill a role (plan: Agent operating model; [ADR 0020](../docs/decisions/0020-eval-harness.md)), and the screen every paper passes before a model reads it ([ADR 0023](../docs/decisions/0023-hidden-text-screen.md)). Its own uv project, so model SDKs stay out of the build's environment.

| Path | Holds |
| --- | --- |
| `roles/` | Role prompts, each versioned in its front matter (`id: extract@0.1.0`); a claim records the version that drafted it |
| `evals/` | The eval harness, the gold set (`evals/gold/`, human-owned) and the scored results |
| `pipeline/` | The literature pipeline on the Batch API ([ADR 0028](../docs/decisions/0028-literature-pipeline.md)): `triage` decides which papers to read; `extract` turns their open full text (abstract, methods, results and captions, screened first) into proposed claim files, checked against a region lexicon; `verify` has a separate prompt judge each claim against the same text, writing the verdict into the claim |
| `curate/` | The gold curation tool: `python -m curate` serves a local page with a paper beside a claim form and atlas-region search, and saves drafts in the gold set's format for the maintainer to review (sprint 0.5a) |
| `screen/` | The hidden-text screen: invisible characters and hidden markup stripped, injection-like paragraphs flagged, with planted fixtures (sprint C.5) |

```bash
cd agents
uv run pytest                                      # the harness's and the screen's tests (pre-commit runs them too)
uv run python -m evals.harness --gold evals/gold/v1 --model anthropic:claude-opus-5-5
uv run python -m screen paper.xml                  # what the screen flags in a JATS or text file
uv run python -m pipeline triage --limit 200       # triage the next 200 papers (ANTHROPIC_API_KEY; a batch, half price)
uv run python -m pipeline triage --limit 5 --now   # a small trial with live calls
uv run --directory .. python -m ingest.lexicon --out .cache/lexicon.json   # the region lexicon extraction needs
uv run python -m pipeline extract --limit 20       # extract the next 20 triaged papers into data/claims/amygdala/
uv run python -m pipeline verify --limit 20        # verify the claims of the next 20 extracted papers
uv run python -m pipeline extract --collect msgbatch_01…   # collect a batch an earlier run left running
uv run python -m pipeline extract --redo 10.1038/nature13186   # read a finished paper again (also: older, all)
uv run python -m pipeline triage --fallback none          # leave refusals refused (default: Opus 5.5's go to Opus 5)
AXONARIUM_SCREEN_MODEL=1 uv run pytest screen      # with the real classifier (downloads about 740 MB once)
```

**Running the pipeline yourself.** Anyone with an Anthropic API key can run it from a checkout:
1. Set `ANTHROPIC_API_KEY`.
2. Build the lexicon once (above).
3. Run a step.

Each step starts where the ledgers in `corpus/` left off and reads each paper once ([corpus/README.md](../corpus/README.md)), so a run can be as small as the credit to hand. Afterwards, `uv run python -m checks sources` from the repository root writes records for newly cited papers. The changes in `corpus/` and `data/` then go to a pull request like any other. The **Literature** workflow does the same from the Actions tab and pushes a branch to open the pull request from; its `extract-and-verify` step runs both, so the claims arrive checked, in one pull request. Batches finish within a day, usually within an hour. A step waits for its batches until five hours after it starts (`--wait`, in minutes; the workflow fits it to the job's six-hour limit). If a batch is still running then, the step writes nothing, exits with code 3 and prints the batch's ID. Run the same step again later with `--collect <batch ID>` (the workflow's `collect` input) to collect the results without paying for them again. In `extract-and-verify`, extracted claims are pushed even when verification's batch is still running; verify them by collecting that batch once their pull request merges.

A flagged paper is never given to a model. The screen's real classifier is pinned to one revision with its files' hashes; `uv run python -m screen --pin` prints a newer one, and moving to it is a reviewed change.

See [evals/README.md](evals/README.md).
