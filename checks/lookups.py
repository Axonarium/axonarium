"""One question per registry: does this term, structure or citation exist, and what does it say about itself."""

import re
from dataclasses import dataclass
from urllib.parse import quote

from checks.http import Fetcher, LookupFailed

OLS = "https://www.ebi.ac.uk/ols4/api/ontologies/{ontology}/terms?obo_id={curie}"
ONTOLOGIES = {"UBERON": "uberon", "CL": "cl", "NCBITaxon": "ncbitaxon"}
ALLEN = "https://api.brain-map.org/api/v2/data/Structure/query.json?criteria=%5Bid%24eq{number}%5D"
ATLAS_GRAPHS = {"MBA": 1, "HBA": 10}  # Allen structure graphs: adult mouse, human
DOI_AGENCY = "https://doi.org/ra/{doi}"
CROSSREF = "https://api.crossref.org/works/{doi}"
DATACITE = "https://api.datacite.org/dois/{doi}"
NCBI = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db={db}&id={uid}&retmode=json"
        "&tool=axonarium-checks&email=admin@axonarium.com")


@dataclass(frozen=True)
class Term:
    exists: bool
    obsolete: bool = False
    replaced_by: str | None = None


def _doi(doi: str) -> str:
    return quote(doi, safe="/")


def ontology_term(fetch: Fetcher, curie: str) -> Term:
    """Whether an UBERON, Cell Ontology or NCBITaxon term exists in OLS, and whether it is obsolete."""
    url = OLS.format(ontology=ONTOLOGIES[curie.split(":")[0]], curie=quote(curie, safe=":"))
    body = fetch.get_json(url)
    if body is None:
        return Term(False)
    terms = body.get("_embedded", {}).get("terms", []) if isinstance(body, dict) else None
    if not isinstance(terms, list):
        raise LookupFailed(url, "unexpected answer from OLS")
    for term in terms:
        if isinstance(term, dict) and term.get("obo_id") == curie:
            return Term(True, term.get("is_obsolete") is True, term.get("term_replaced_by") or None)
    return Term(False)


def atlas_structure(fetch: Fetcher, curie: str) -> Term:
    """Whether an MBA or HBA ID is a structure in its Allen structure graph."""
    prefix, number = curie.split(":")
    url = ALLEN.format(number=number)
    body = fetch.get_json(url)
    if not isinstance(body, dict) or body.get("success") is not True or not isinstance(body.get("msg"), list):
        raise LookupFailed(url, "unexpected answer from the Allen API")
    return Term(any(isinstance(s, dict) and s.get("id") == int(number) and s.get("graph_id") == ATLAS_GRAPHS[prefix]
                    for s in body["msg"]))


def doi_agency(fetch: Fetcher, doi: str) -> str | None:
    """The DOI's registration agency (such as Crossref or DataCite), or None if the DOI doesn't exist."""
    url = DOI_AGENCY.format(doi=_doi(doi))
    body = fetch.get_json(url)
    if body is None:
        return None
    entry = body[0] if isinstance(body, list) and body and isinstance(body[0], dict) else None
    if entry is not None and isinstance(entry.get("RA"), str):
        return entry["RA"]
    if entry is not None and entry.get("status") in ("DOI does not exist", "Invalid DOI"):
        return None
    raise LookupFailed(url, "unexpected answer from doi.org")


def crossref_work(fetch: Fetcher, doi: str) -> dict | None:
    """Crossref's metadata for a DOI (its `message`), or None if Crossref has no record."""
    url = CROSSREF.format(doi=_doi(doi))
    body = fetch.get_json(url)
    if body is None:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("message"), dict):
        raise LookupFailed(url, "unexpected answer from Crossref")
    return body["message"]


def datacite_record(fetch: Fetcher, doi: str) -> dict | None:
    """DataCite's attributes for a DOI, or None if DataCite has no record."""
    url = DATACITE.format(doi=_doi(doi))
    body = fetch.get_json(url)
    if body is None:
        return None
    attributes = body.get("data", {}).get("attributes") if isinstance(body, dict) and isinstance(body.get("data"), dict) else None
    if not isinstance(attributes, dict):
        raise LookupFailed(url, "unexpected answer from DataCite")
    return attributes


def ncbi_summary(fetch: Fetcher, db: str, uid: str) -> dict | None:
    """NCBI's summary of a PubMed (db "pubmed") or PubMed Central (db "pmc", number only) record; None if none."""
    url = NCBI.format(db=db, uid=quote(uid, safe=""))
    body = fetch.get_json(url)
    result = body.get("result") if isinstance(body, dict) else None
    summary = result.get(uid) if isinstance(result, dict) else None
    if not isinstance(summary, dict):
        raise LookupFailed(url, "unexpected answer from NCBI")
    return None if "error" in summary else summary


def arxiv_doi(arxiv_id: str) -> str:
    """The DataCite DOI arXiv registers for a preprint (all versions share it)."""
    return "10.48550/arXiv." + re.sub(r"v\d+$", "", arxiv_id)
