---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# Online identifier and citation checks

## Context and Problem Statement

Agents will extract claims from papers (sprint 2.3), and language models invent plausible identifiers: ontology terms, atlas regions, DOIs and PubMed IDs that don't exist or point elsewhere. The schema can only check an identifier's shape. The plan also says that claims citing retracted papers are flagged, not silently deleted, and that verbatim excerpts come only from openly licensed papers. How does the project know that an identifier is real, that a paper hasn't been retracted, and what its licence is?

## Considered Options

* Look identifiers up in the registries that own them, on every pull request that changes data, and keep a source record per cited DOI
* Download the ontologies and registries and check offline
* Check only at release time

## Decision Outcome

Chosen option: "look identifiers up in their registries", because only the registries know what exists today, and a pull request is where an invented identifier must stop.

* **Registries:** EBI OLS for UBERON, Cell Ontology and NCBITaxon (existence and obsolescence); the Allen Brain Map API for MBA and HBA structures; doi.org for whether a DOI exists; Crossref, whose records include Retraction Watch data, and DataCite for DOI metadata; NCBI E-utilities for PubMed and PubMed Central IDs. arXiv IDs are checked through their DataCite DOIs.
* **Fail closed:** a lookup that still fails after retries fails the check, so nothing unverified merges during an outage; the cost is an occasional re-run.
* **Source records:** every citation has a record in `data/sources/`, written by `python -m checks sources`, keyed by its DOI, else its PubMed ID, else its PubMed Central ID, else its arXiv ID. DOI records come from Crossref or DataCite, PubMed records from NCBI (retracted when PubMed lists the type "Retracted Publication"), arXiv records from DataCite. A citation must carry the DOI, and the PubMed ID, that its PubMed or PubMed Central record names (`citation-incomplete`), so modern papers always go through Crossref's retraction data. *Amended 3 October 2026 (sprint 0.3c); previously DOI records only.*
* **Retractions:** a claim citing a retracted paper must itself be `retracted`, which needs a log entry and the maintainer's review ([ADR 0006](0006-deletion-and-retraction-review.md)).
* **Excerpts:** only from papers under CC BY (any version) or CC0, because project data is CC BY 4.0 ([ADR 0002](0002-licensing.md)) and share-alike, non-commercial or no-derivatives terms would not carry over. Other papers get paraphrases.
* **Re-checks:** papers retracted after their claims merged are caught when a pull request touches the claim or its source, and by the release job (sprint 3.2), which runs the full check and refreshes every source record.
* **Allen content** is looked up at check time and cached only in a git-ignored folder, never committed ([ADR 0005](0005-source-reuse-terms.md)).

### Consequences

* Good, because invented terms, regions and citations fail CI with a rule naming the problem, before any review.
* Good, because licence and retraction status live in reviewable files, and CI compares them with the registries, so they can't be hand-edited to permit an excerpt.
* Bad, because pull requests that change data depend on six external services; an outage blocks merging until a re-run succeeds.
* Neutral: tests replay recorded registry responses, so the test suite runs without the network; the recordings are refreshed with `AXONARIUM_RECORD=1`.
