---
status: accepted
date: 2026-10-14
decision-makers: Tyler Banks
consulted: Claude (coverage beyond open-access papers)
---

# Full text from PMC's open data when Europe PMC won't serve it

## Context and Problem Statement

Extraction reads only the papers whose full text Europe PMC serves through its `fullTextXML` endpoint: its open-access subset (ADR 0028). Of the 1,608 papers triaged in, that left out:

* 347 papers with a PMC ID that aren't open access, which Europe PMC holds but won't serve. 161 of them are author manuscripts.
* 11 open-access papers Europe PMC answers with a server error every time, so extraction set them aside. All 11 are author manuscripts in PMC, six of them from *Nature* journals.
* 4 open-access preprints that have only a Europe PMC preprint ID (`PPR…`), no PMC ID.

PMC shares its open-access and author manuscript datasets on AWS (`s3://pmc-oa-opendata`, part of the PMC Cloud Service). The bucket is public and needs no credentials, and each article has JSON metadata giving its licence code, its manuscript status and the MD5 of its JATS XML. On 14 October 2026 it held 172 of the papers above: the 161 manuscripts (licence code `TDM`, PMC's terms for text mining) and all 11 that fail on Europe PMC. How should extraction reach them?

## Considered Options

* PMC's open data as a second source, tried when Europe PMC won't serve a PMC paper
* PMC's open data as the only source of full text
* NCBI's own APIs (E-utilities, the BioC API)
* Leave these papers to abstract-only extraction

## Decision Outcome

Chosen option: "PMC's open data as a second source". It reaches 172 more papers with the prompts, screen and checks the pipeline already has, and it changes nothing for the 317 papers already read from Europe PMC.

* **Order:** `europepmc.full_text` asks Europe PMC first. When Europe PMC answers a PMC ID with an HTTP error, it looks for the paper's newest version in the bucket, downloads its JATS XML and checks the MD5. If the bucket doesn't have the paper, Europe PMC's error stands, so a 404 still records `unavailable` and a repeated server error is still set aside (ADR 0028).
* **Candidates:** extraction no longer requires open access. Any paper triaged in, with full text in Europe PMC and a PMC or preprint ID, is a candidate. A paper neither source serves is recorded `unavailable` once, without reaching a model: about 186 papers, 121 of them *J Neurosci*, are in neither of PMC's datasets.
* **Preprints:** a paper with only a Europe PMC preprint ID is fetched by that ID, if its server is one the allowlist accepts (ADR 0015). Of the 4, the 3 bioRxiv preprints qualify. The Research Square one doesn't, and its published version has been read already.
* **Terms:** the manuscripts' `TDM` licence permits text mining, not republishing. ADR 0005 already allows paraphrased claims and locators from any paper, and the schema allows an `excerpt` only from CC BY or CC0 papers (ADR 0007). Neither changes, and full text is still never committed, only cached in `.cache/papers`.
* **The 11 set-aside papers** come back with `--redo` naming them, since a set-aside paper waits for a redo.

### Consequences

* Good, because about 175 more papers can be read, an estimated 1,500 to 1,800 claims, at the usual $0.25 to $0.35 a paper for extraction and verification.
* Good, because the bucket gives a file's MD5, so a damaged download is caught before the screen reads it.
* Good, because it needs no new dependency: the same HTTP helper reads a public HTTPS endpoint.
* Bad, because the first run spends about 186 slots of its paper limit on papers that turn out `unavailable`. They cost no tokens, and each is tried only once.
* Neutral: a paper Europe PMC fails on costs its retries (about 14 seconds) before the bucket is asked.
* Neutral: Europe PMC's full text for preprint IDs is assumed from its documentation. The agents' sandbox can't reach Europe PMC, so the first run is the test. A preprint it won't serve is recorded `unavailable`.

## Pros and Cons of the Options

### PMC's open data as the only source

* Good, because one source is simpler.
* Bad, because the 317 papers read so far came from Europe PMC, and verification reads the same text again. Switching sources could shift the locators the claims cite.

### NCBI's APIs

* Bad, because E-utilities serve the same XML with rate limits and an API key to manage, and the BioC API serves BioC rather than JATS, so the screen and the pruning would need a second parser.

### Abstract-only extraction for these papers

* Bad, because an abstract holds far fewer claims than a full text, with no figure locators or numbers. It remains an option for the 899 papers with no full text anywhere.
