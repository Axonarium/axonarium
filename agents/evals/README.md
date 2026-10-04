# Evals

The gold set is the project's anchor: a frozen, human-curated sample that every model and prompt must pass before it touches the data (plan: Quality and validation). This harness scores a model and a role prompt against it ([ADR 0020](../../docs/decisions/0020-eval-harness.md)). The gold set and these files are human-owned: they change only when a sprint card says so, with the maintainer's review.

## Running

From `agents/`:

```bash
uv run python -m evals.harness --gold evals/gold/v1 --model anthropic:claude-opus-5-5 --prompt roles/extractor.md
uv run python -m evals.harness --gold evals/gold/v1 --model openai:<model> --effort high
uv run python -m evals.harness --gold evals/fixtures/placeholder --model replay:evals/fixtures/placeholder/answers
```

| Option | Means |
| --- | --- |
| `--model` | `anthropic:<model>` (Anthropic SDK; `ANTHROPIC_API_KEY`), `openai:<model>` (OpenAI SDK; `OPENAI_API_KEY`), or `replay:<folder>` (saved answers, `<folder>/<paper>.json`) |
| `--prompt` | A role prompt with a versioned `id` in its front matter (default `roles/extractor.md`) |
| `--effort` | The model's effort or reasoning level (default `high`); `none` leaves it unset, for models without one |
| `--out` | Where the report goes (default `evals/results/`) |

Every run calls the model once per paper and **costs money**; the report gives the tokens used. A model that refuses, runs out of tokens or returns output that doesn't fit the schema is recorded as a failure on that paper, never retried on another model: an eval scores the model it names.

## Scores

A predicted claim matches a gold claim when they name the same subject, predicate, object and species.

| Score | Is |
| --- | --- |
| Precision, recall, F1 | Over connections (claims with the same subject, predicate, object and species count once) |
| Field accuracy | On matched connections: method (evidence class), result and sign |
| Absent recall | Of the gold connections tested and not found, those the model also reports as absent |
| Direction errors | Predictions that are a gold connection reversed |
| Species errors | Predictions that match a gold connection in another species |

The plan's proposed bar is precision and field accuracy of at least 0.90 to run unattended; a candidate model replaces the incumbent only if it matches or beats it.

## The gold set's format

`evals/gold/<version>/`, frozen once reviewed (gold v1, then v2 and so on, each by human review):

```
gold.yaml              version, frozen (date), curators, notes
papers/<name>.yaml     one paper: its source, where its text is, and every claim it makes
texts/<name>.txt       a paper's text, only for synthetic or CC BY / CC0 papers (ADR 0005)
```

```yaml
source: {doi: 10.1038/s41467-021-22915-5, pmcid: PMC8129205}
text: {europe_pmc: PMC8129205}        # or {file: texts/<name>.txt}
claims:
  - subject: {type: region, id: "MBA:295"}
    predicate: projects_to
    object: {type: region, id: "MBA:536"}
    species: "NCBITaxon:10090"
    evidence_class: anterograde_tracer
    result: present                    # absent for tested-and-not-found pairs
    sign: unknown
    locator: Fig. 3B
```

Open-access text is fetched from Europe PMC when a run needs it and cached in `.cache/papers/`, never committed. `evals/fixtures/placeholder/` is a synthetic stand-in that exercises the harness until gold v1 exists.
