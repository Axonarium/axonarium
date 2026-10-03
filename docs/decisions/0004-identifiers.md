---
status: accepted
date: 2026-10-02
decision-makers: Tyler Banks
---

# Identifiers

## Context and Problem Statement

Every claim, neuron type and entity reference needs an identifier that stays valid as the project grows, survives forks and changes of maintainer, and can be minted by agents working in parallel without coordinating. How should Axonarium form its identifiers?

## Considered Options

* Base URI: `https://w3id.org/axonarium/` or `https://axonarium.org/id/`
* Record IDs: a type prefix plus 10 random characters, sequential numbers (`clm-000123`), or ULIDs
* Regions: atlas region IDs only, or atlas region IDs and UBERON terms

## Decision Outcome

Chosen options:

* **Base URI `https://w3id.org/axonarium/`**, because w3id.org redirects are community-maintained and keep working if the project's domain lapses. Registering the redirect is a separate pull request to the w3id.org registry; until then the IDs are valid but don't resolve.
* **Prefixed random IDs**: `clm-` for connectivity claims, `hom-` for homology claims and `nt-` for neuron types, then 10 characters from `0123456789abcdefghjkmnpqrstvwxyz` (lowercase Crockford base32, without i, l, o or u). Agents never need to coordinate, and the IDs stay short. Sequential numbers would collide when two agents add claims at the same time, and ULIDs are 26 characters long. Sprint 0.3's uniqueness check catches the rare collision.
* **Regions are atlas region IDs with their pinned atlas** (`MBA:295` with `allen-mouse-ccf-2017`), **or UBERON terms** where no atlas is pinned yet. Every claim states its species, so regions in different species never merge.
* Species use NCBI Taxonomy (`NCBITaxon:10090`). Neuron types without a project ID use the Cell Ontology. Sources use `doi:`, `pubmed:`, `pmc:` or `arxiv:` CURIEs. MBA and HBA expand to BICAN's ontology PURLs rather than the Bioregistry's provider pages, so `.linkmllint.yaml` checks prefixes against OBO only.

### Consequences

* Good, because IDs need no central counter, survive a lapsed domain, and expand to full URIs for linked-data exports.
* Bad, because random IDs carry no meaning or order; search and the explorer have to provide that.
* Bad, because rat and human claims stay at UBERON granularity until sprint 1.2 pins those atlases.
