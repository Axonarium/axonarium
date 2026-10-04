---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint C.2)
---

# The source allowlist: kinds of publication, typed by their registries

## Context and Problem Statement

The plan's second defence against poisoned evidence (Part 3.3, "Layer 2") is an allowlist of source types, not domains: peer-reviewed journal articles and the major preprint servers (bioRxiv, medRxiv, arXiv), with preprints tagged as a lower evidence tier, and everything else refused. It is to live in `data/allowlist.yaml`, owned by the maintainer, and the validator is to enforce it (sprint C.2). Source records (`data/sources/`) held a paper's title, year, journal, licence and retraction status, but nothing said what kind of publication it was. How does the validator know, and how does the allowlist say what it accepts?

## Considered Options

* Each source record states its kind, as its registry types it; the allowlist lists accepted kinds, and optionally venues
* The allowlist lists DOI prefixes or journal names
* The online checks ask the registries for the type on every run; nothing is stored

## Decision Outcome

Chosen option: "each source record states its kind", because the registries already type every publication, `checks sources` already writes source records from them, and the online checks already compare a record's `license` and `retracted` with its registry, so `kind` gets the same protection.

* **Schema 0.4.0:** `Source` gains a required `kind`: `journal_article`, `preprint`, `dataset` or `other`. New classes `Allowlist` and `AcceptedSource` describe `data/allowlist.yaml`: a list of accepted kinds, each with an optional list of `venues` and a `reason`.
* **Where a kind comes from** (`checks/sources.py`):

  | Registry | `journal_article` | `preprint` | `dataset` |
  | --- | --- | --- | --- |
  | Crossref | type `journal-article` | type `posted-content`, subtype `preprint`; the venue is the posting institution (`bioRxiv`, `medRxiv`) | type `dataset` |
  | DataCite | `resourceTypeGeneral` `JournalArticle` | `Preprint`, or any arXiv DOI (`10.48550/arXiv.…`) | `Dataset` |
  | PubMed | publication type `Journal Article` or `Review` | publication type `Preprint`; the venue is NCBI's name for the server | |
  | PubMed Central | every record not from a preprint server | `bioRxiv`, `medRxiv`, `arXiv` or `Res Sq` as the journal | |

  Anything else is `other`, including DOIs from registration agencies other than Crossref and DataCite. A preprint's `journal` is its server, so the allowlist can name servers.
* **The allowlist** (`data/allowlist.yaml`) accepts journal articles and preprints from arXiv, bioRxiv and medRxiv. `python -m checks files` reports `source-not-allowed` for any claim whose source record matches no entry. Without an allowlist, no source is accepted: the check fails closed. The build applies the same rule to the claims it makes at build time.
* **Protection:** the online checks compare a record's `kind` and `journal`, as well as its licence and retraction status, with its registry (`source-outdated`), so a hand edit can't move a source onto the allowlist. CODEOWNERS names `data/allowlist.yaml` explicitly, so every change to it needs the maintainer.
* **Tiers:** preprints are tagged by `kind: preprint`, which the read API returns with each source and the claim page shows. Nothing ranks evidence yet; when edges or answers rank claims, published work ranks above preprints.
* **Database:** the `sources` table gains a `kind` column (migration `446a2dbdfbba`).

### Consequences

* Good, because the rule is the plan's: source types, not domains, enforced offline on every pull request and in every build.
* Good, because the community inbox (sprint C.1) and triage (C.4) can apply the same rule to a submitted identifier through the same code.
* Bad, because a registry's type is a proxy: Crossref's `journal-article` doesn't prove peer review, and a predatory journal's articles pass. The verifier and the audit sample remain the defence there.
* Bad, because journal articles registered with agencies other than Crossref and DataCite (such as mEDRA or JaLC) are typed `other` and refused, unless they are cited by PubMed ID. A future allowlist change can accept them.
* Neutral: datasets are refused for now. A curated knowledge base such as SCKAN (moved to Phase 7a) would need its own allowlist entry, and its own evidence class.

### Confirmation

`checks/tests/test_files.py` covers venues, a missing allowlist and the project's own allowlist; `checks/tests/test_sources.py` covers each registry's typing; `checks/tests/test_online.py` covers the comparison with the registry; `build/tests/test_connectivity.py` covers a build-time claim citing a refused source.
