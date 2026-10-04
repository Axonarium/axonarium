---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint 2.2)
---

# The literature corpus: saved Europe PMC searches and a committed manifest

## Context and Problem Statement

Extraction (sprint 2.3) needs a list of the papers to read. The plan's sprint 2.2 asks for "saved PubMed queries, open-access full text, dedup", with a committed corpus manifest. The Scout role runs saved queries and queues new papers, and never extracts. The building blocks name NCBI E-utilities, Europe PMC and Crossref for literature access. Which service runs the queries, what does the manifest hold, and how does it change?

## Considered Options

* Europe PMC's search API for queries and metadata in one call
* PubMed through NCBI E-utilities, then Europe PMC or PubMed Central for open-access status, licences and full text
* PubTator 3 searches

## Decision Outcome

Chosen option: "Europe PMC's search API", because Europe PMC indexes all of PubMed and the preprint servers the allowlist accepts (ADR 0015). One search answers with each paper's identifiers, publication types, open-access status, licence and whether it holds the full text. That is everything the manifest needs, with no second service.

* **Queries:** `corpus/queries.yaml`, in Europe PMC's syntax, each with an ID and the reason it exists. Four to start: tract tracing, optogenetic circuit mapping, synaptic evidence, and connection words in titles. All cover rats and mice, from PubMed (`SRC:MED`) and preprints (`SRC:PPR`). A query finding more than 20,000 papers stops the scout, since it is too broad to read.
* **Scout:** `python -m ingest.scout` runs each query through the checks' retried, rate-limited session (ADR 0012), 1,000 results a page with cursor marks.
* **Manifest:** `corpus/manifest.csv`, one row per paper, merged across queries and records by DOI, PubMed ID and PubMed Central ID, keyed like source records (DOI, else PubMed ID, else PubMed Central ID). It holds identifiers, title, year, journal (a preprint's server), publication types, open-access status, licence, full-text availability, the queries that found it and the date it was first seen. It never holds abstracts or full text (ADR 0005). CSV, sorted, so a run's diff shows exactly which papers came and went.
* **Runs:** the **Scout** workflow (manual for now, weekly in Phase 6) pushes the new manifest to a `scout/<date>` branch. A pull request opened with the workflow's own token wouldn't run CI, so the maintainer opens it from that branch. The workflow can push branches, never `main`.
* **Full text:** read from Europe PMC by the extractor when it reads a paper (sprint 2.3), after hidden text is stripped (sprint C.5); never committed.

### Consequences

* Good, because one free, open API covers the queries, open-access status and licences, and includes preprints.
* Good, because every change to the corpus is a reviewed diff, and `first_seen` gives the extractor its next batch.
* Bad, because Europe PMC's query syntax isn't PubMed's: queries can't be pasted into PubMed unchanged.
* Bad, because a preprint and its published version have different DOIs and stay two rows; extraction treats the published version as the source.
* Neutral: `manifest.csv` holds bibliographic metadata under the repository's default licence in `REUSE.toml`; the maintainer may prefer to annotate `corpus/` as CC0-1.0, a governance-file change.
