# Corpus

The literature the amygdala module reads (sprint 2.2, [ADR 0019](../docs/decisions/0019-literature-corpus.md)).

| File | Holds |
| --- | --- |
| `queries.yaml` | The saved searches, in Europe PMC's syntax, each with why it exists. Changes need the maintainer's review |
| `manifest.csv` | Every paper the searches find, one row each, written by the scout. Never edited by hand |
| `triage.csv` | The pipeline's triage verdict for each paper: whether its own data test a connection ([ADR 0028](../docs/decisions/0028-literature-pipeline.md)). Written by `python -m pipeline triage` |

Run the scout from the repository root, or with the **Scout** workflow in the Actions tab, which pushes the result to a `scout/<date>` branch to open a pull request from:

```bash
uv run python -m ingest.scout
```

## The manifest

One row per paper, sorted by `key`: its DOI, else PubMed ID, else PubMed Central ID, as in `data/sources/`. Papers found by several queries, or as several Europe PMC records sharing an identifier, are one row.

| Column | Holds |
| --- | --- |
| `key`, `doi`, `pmid`, `pmcid` | Identifiers |
| `europe_pmc` | Europe PMC's source and ID, such as `MED:34001873` or `PPR:PPR123` |
| `title`, `year`, `journal` | Bibliographic metadata; a preprint's journal is its server |
| `types` | Europe PMC's publication types, such as `research-article` or `review` |
| `open_access`, `license`, `full_text` | Whether the paper is open access, under which licence (as Europe PMC gives it), and whether Europe PMC holds its full text for the extractor |
| `queries` | The queries that found it |
| `first_seen` | The day the scout first found it: a run's new papers are the extractor's next batch |

Abstracts and full text are never stored here (ADR 0005). Extraction (sprint 2.3) reads open-access full text from Europe PMC when it needs it.

## Triage

`triage.csv` has one row per paper, sorted by `key`, from sprint 2.2a. A paper is triaged once per version of the triage prompt; a failed request is tried again on the next run.

| Column | Holds |
| --- | --- |
| `verdict` | `in` (worth reading for claims), `out`, or why the request failed (`refusal`, `invalid`, `errored`, `expired`, …) |
| `basis` | `abstract`, or `title` when Europe PMC has no abstract |
| `evidence`, `species` | The kinds of evidence and the species the abstract describes, `;`-separated |
| `reason` | One sentence in the model's own words, never the abstract's |
| `model`, `prompt`, `date` | Which model and prompt version decided, and when |

The manifest grows with every run, past pre-commit's 500 KB limit for added files, so that check skips it. It stays one file, so a run's diff shows which papers came and went.
