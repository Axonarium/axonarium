# Corpus

The literature the amygdala module reads (sprint 2.2, [ADR 0019](../docs/decisions/0019-literature-corpus.md)).

| File | Holds |
| --- | --- |
| `queries.yaml` | The saved searches, in Europe PMC's syntax, each with why it exists. Changes need the maintainer's review |
| `manifest.csv` | Every paper the searches find, one row each, written by the scout. Never edited by hand |
| `triage.csv` | The pipeline's triage verdict for each paper: whether its own data test a connection ([ADR 0028](../docs/decisions/0028-literature-pipeline.md)). Written by `python -m pipeline triage` |
| `extracted.csv` | What extraction did with each paper: how many claims it gave, or why it gave none. Written by `python -m pipeline extract` |

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

## Reading each paper once

The ledgers below record every paper the literature pipeline has handled (ADR 0028), and each step reads a paper once:
- **A finished paper is never sent again**, whatever version of the prompt finished it. Reading it again takes an explicit `--redo`: named papers (key, DOI, PubMed ID or PMC ID), `older` (finished by an earlier prompt version) or `all`.
- **A paper whose answers fail** (a refusal, a cut-off or invalid answer) is tried again, and set aside after two reads. Batch entries no model answered (errored, expired) don't count.
- **A refused paper goes to a second model in the same run:** Claude Opus 5.5's refusals go to Claude Opus 5 (`--fallback`). That counts as one read, and the row names the model that answered.
- **A paper is the same paper under any of its identifiers:** one keyed by its PubMed ID that later gains a DOI is still recognised.
- **A run refuses to start while another branch holds this step's results** that aren't on its own branch yet. Merge that run's pull request first.

## Triage

`triage.csv` has one row per paper, sorted by `key`, from sprint 2.2a.

| Column | Holds |
| --- | --- |
| `verdict` | `in` (worth reading for claims), `out`, or why the request failed (`refusal`, `invalid`, `errored`, `expired`, …) |
| `basis` | `abstract`, or `title` when Europe PMC has no abstract |
| `evidence`, `species` | The kinds of evidence and the species the abstract describes, `;`-separated |
| `reason` | One sentence in the model's own words, never the abstract's; for a refusal, its category, such as `bio` |
| `attempts` | How many times a model has read it for this step |
| `model`, `prompt`, `date` | Which model and prompt version decided (the fallback, when it answered a refusal), and when |

## Extraction

`extracted.csv` has one row per paper extraction has handled, sorted by `key`, from sprint 2.3.

| Column | Holds |
| --- | --- |
| `outcome` | `claims` (it gave claims), `none` (it tests no connection the extractor could state), `screened` (the hidden-text screen flagged it, so no model read it), `unreadable` (its full text didn't parse), `unfetched` (Europe PMC couldn't be reached; tried again next run), or why the request failed |
| `claims`, `dropped` | Claims written, and drafts dropped for naming a region outside the lexicon or breaking the schema's rules |
| `attempts` | How many times a model has read it for this step |
| `model`, `prompt`, `date` | Which model and prompt version extracted (the fallback, when it answered a refusal), and when |

## Verification

`verified.csv` has one row per paper verification has sent, sorted by `key`, from sprint 2.4. The verdicts themselves are in the claims.

| Column | Holds |
| --- | --- |
| `outcome` | `judged` (the verifier answered), `screened`, `unreadable`, `unfetched`, or why the request failed |
| `claims`, `judged` | Claims listed in the request, and how many got a verdict |
| `listed` | A short hash of the paper and the claims listed: tries are counted per list |
| `attempts` | How many times a model has read this list of claims |
| `model`, `prompt`, `date` | Which model and prompt version verified (the fallback, when it answered a refusal), and when |

The manifest and the ledgers grow with every run, past pre-commit's 500 KB limit for added files, so that check skips them. Each stays one file, so a run's diff shows which papers came and went.
