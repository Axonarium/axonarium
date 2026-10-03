"""Each registry answers one question; responses are replayed from real recordings."""

import json

import pytest

from checks.http import Fetcher
from checks.lookups import Term, arxiv_doi, atlas_structure, doi_agency, ncbi_summary, ontology_term
from checks.tests.conftest import RECORDED


@pytest.mark.parametrize("curie, term", [
    ("UBERON:0002883", Term(True)),
    ("UBERON:0001006", Term(True, obsolete=True)),
    ("UBERON:9999999", Term(False)),
    ("CL:0000679", Term(True)),
    ("NCBITaxon:10090", Term(True)),
])
def test_ontology_term(fetch, curie, term):
    assert ontology_term(fetch, curie) == term


@pytest.mark.parametrize("curie, exists", [
    ("MBA:295", True),
    ("HBA:4249", True),
    ("MBA:4249", False),  # a human structure, not in the mouse graph
    ("MBA:999999999", False),
    ("DHBA:10361", True),  # amygdaloid complex, Allen graph 16 (the Ding et al. 2016 human atlas)
    ("MBA:10361", False),
])
def test_atlas_structure(fetch, curie, exists):
    assert atlas_structure(fetch, curie) == Term(exists)


@pytest.mark.parametrize("doi, agency", [
    ("10.1038/s41467-021-22915-5", "Crossref"),
    ("10.48550/arXiv.2409.13740", "DataCite"),
    ("10.5555/axonarium.example.001", None),
])
def test_doi_agency(fetch, doi, agency):
    assert doi_agency(fetch, doi) == agency


def test_ncbi_summary(fetch):
    found = ncbi_summary(fetch, "pubmed", "34001873")
    assert {"idtype": "doi", "value": "10.1038/s41467-021-22915-5"} in [
        {"idtype": a["idtype"], "value": a["value"]} for a in found["articleids"]]
    assert ncbi_summary(fetch, "pubmed", "99999999999") is None


def test_arxiv_doi():
    assert arxiv_doi("2409.13740v2") == arxiv_doi("2409.13740") == "10.48550/arXiv.2409.13740"


def test_doi_is_quoted_in_requests():
    sent = []

    def opener(url, headers, timeout):
        sent.append(url)
        return 200, {}, json.dumps([{"DOI": "x", "status": "DOI does not exist"}]).encode()

    doi = "10.1002/(sici)1096-9861(19960101)364:1<1::aid-cne1>3.0.co;2-#"
    assert doi_agency(Fetcher(None, opener, sleep=lambda s: None), doi) is None
    assert sent == ["https://doi.org/ra/10.1002/%28sici%291096-9861%2819960101%29364%3A1%3C1%3A%3Aaid-cne1%3E3.0.co%3B2-%23"]


def test_recordings_hold_no_allen_or_ontology_text():
    # ADR 0005: Allen content is never committed; ontology labels would need attribution. Keep only what the checks read.
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))
    for url, entry in recorded.items():
        body = entry["body"] or {}
        if "api.brain-map.org" in url:
            assert all(set(s) <= {"id", "graph_id"} for s in body.get("msg", [])), url
        if "www.ebi.ac.uk/ols4" in url:
            assert all(set(t) <= {"obo_id", "is_obsolete", "term_replaced_by"} for t in body.get("_embedded", {}).get("terms", [])), url
