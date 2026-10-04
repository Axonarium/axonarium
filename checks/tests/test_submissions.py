"""Vetting a submitted paper identifier (sprint C.1): canonical form, existence, retraction and the allowlist."""

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from checks.http import Fetcher
from checks.submissions import canonical_identifier, vet
from checks.tests.conftest import OpenerAdapter, REPO

TODAY = date(2026, 10, 3)
ALLOWLIST = yaml.safe_load((REPO / "data" / "allowlist.yaml").read_text(encoding="utf-8"))["accepted"]


@pytest.mark.parametrize("raw,expected", [
    ("10.1038/s41467-021-22915-5", "doi:10.1038/s41467-021-22915-5"),
    ("  doi:10.1038/S41467-021-22915-5 ", "doi:10.1038/s41467-021-22915-5"),
    ("DOI: 10.1038/s41467-021-22915-5", "doi:10.1038/s41467-021-22915-5"),
    ("https://doi.org/10.1038/s41467-021-22915-5", "doi:10.1038/s41467-021-22915-5"),
    ("http://dx.doi.org/10.1016/S0140-6736(97)11096-0", "doi:10.1016/s0140-6736(97)11096-0"),
    ("https://doi.org/10.1016%2FS0140-6736%2897%2911096-0", "doi:10.1016/s0140-6736(97)11096-0"),
    ("https://www.biorxiv.org/content/10.1101/2020.01.01.000001v2.full", "doi:10.1101/2020.01.01.000001"),
    ("https://www.medrxiv.org/content/10.1101/2021.05.06.21256745v1", "doi:10.1101/2021.05.06.21256745"),
    ("34001873", "pubmed:34001873"),
    ("PMID: 34001873", "pubmed:34001873"),
    ("https://pubmed.ncbi.nlm.nih.gov/34001873/", "pubmed:34001873"),
    ("https://www.ncbi.nlm.nih.gov/pubmed/34001873", "pubmed:34001873"),
    ("https://europepmc.org/article/MED/34001873", "pubmed:34001873"),
    ("PMC8129205", "pmc:PMC8129205"),
    ("pmcid: pmc8129205", "pmc:PMC8129205"),
    ("https://pmc.ncbi.nlm.nih.gov/articles/PMC8129205/", "pmc:PMC8129205"),
    ("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8129205/", "pmc:PMC8129205"),
    ("https://europepmc.org/article/PMC/PMC8129205", "pmc:PMC8129205"),
    ("2409.13740", "arxiv:2409.13740"),
    ("arXiv:2409.13740v2", "arxiv:2409.13740"),
    ("https://arxiv.org/abs/2409.13740v1", "arxiv:2409.13740"),
    ("https://arxiv.org/pdf/2409.13740v1.pdf", "arxiv:2409.13740"),
])
def test_identifiers_become_canonical(raw, expected):
    assert canonical_identifier(raw) == expected


@pytest.mark.parametrize("raw", [
    "", "   ", "a paper about the amygdala", "https://bit.ly/3xyz", "https://example.com/paper.pdf",
    "https://someblog.org/10.1038/s41467-021-22915-5", "10.1038", "doi:10.1038/", "PMC", "0", "1234567890",
    "https://doi.org/10.1038/s41467-021-22915-5 and more", "10.1038/s41467\n021", "x" * 400,
    "https://www.biorxiv.org/content/early/2020/01/01/000001", "javascript:alert(1)",
])
def test_anything_else_is_malformed(raw):
    assert canonical_identifier(raw) is None


def vetted(fetch, raw):
    return vet(raw, fetch, TODAY, ALLOWLIST)


@pytest.mark.parametrize("raw,source_id", [
    ("https://doi.org/10.1038/s41467-021-22915-5", "doi:10.1038/s41467-021-22915-5"),
    ("PMID 1023575", "pubmed:1023575"),
    ("arXiv:2409.13740", "arxiv:2409.13740"),
])
def test_existing_allowed_papers_are_accepted(fetch, raw, source_id):
    result = vetted(fetch, raw)
    assert (result.status, result.source_id) == ("accepted", source_id) and result.record["id"] == source_id


@pytest.mark.parametrize("raw,status", [
    ("not an identifier", "malformed"),
    ("10.5555/axonarium.missing.001", "unknown"),
    ("99999999999", "malformed"),  # more digits than any PubMed ID
    ("10.1016/S0140-6736(97)11096-0", "retracted"),  # retracted, per Crossref
    ("10.1503/jpn.120073", "retracted"),  # retracted per PubMed, though not per Crossref
    ("11134581", "retracted"),  # a PubMed ID PubMed lists as retracted
])
def test_malformed_unknown_and_retracted_identifiers_are_rejected(fetch, raw, status):
    result = vetted(fetch, raw)
    assert result.status == status and result.record is None and result.reason


def test_unknown_arxiv_ids_are_rejected(replay):
    def opener(url, headers, timeout):
        if url == "https://api.datacite.org/dois/10.48550/arXiv.2409.99999":
            return 404, {}, b""
        return replay(url, headers, timeout)

    result = vet("https://arxiv.org/abs/2409.99999v1", Fetcher(None, OpenerAdapter(opener)), TODAY, ALLOWLIST)
    assert (result.status, result.source_id) == ("unknown", "arxiv:2409.99999")


def test_kinds_the_allowlist_refuses_are_rejected(replay):
    chapter = "https://api.crossref.org/works/10.5555/book.chapter"

    def opener(url, headers, timeout):
        if url == "https://doi.org/ra/10.5555/book.chapter":
            return 200, {}, json.dumps([{"DOI": "10.5555/book.chapter", "RA": "Crossref"}]).encode()
        if url == chapter:
            return 200, {}, json.dumps({"message": {"type": "book-chapter", "title": ["A chapter"]}}).encode()
        if "esearch" in url:
            return 200, {}, json.dumps({"esearchresult": {"count": "0", "idlist": []}}).encode()
        return replay(url, headers, timeout)

    result = vet("10.5555/book.chapter", Fetcher(None, OpenerAdapter(opener)), TODAY, ALLOWLIST)
    assert result.status == "not-allowed" and "other" in result.reason


def test_a_registry_that_cannot_be_asked_is_reported_not_rejected():
    def down(url, headers, timeout):
        raise OSError("connection refused")

    result = vet("10.1038/s41467-021-22915-5", Fetcher(None, OpenerAdapter(down)), TODAY, ALLOWLIST)
    assert result.status == "lookup-failed" and result.source_id == "doi:10.1038/s41467-021-22915-5"


def test_vetting_never_runs_on_an_identifier_it_cannot_canonicalise(replay):
    asked = []

    def opener(url, headers, timeout):
        asked.append(url)
        return replay(url, headers, timeout)

    vet("https://evil.example/?q=10.1038/x", Fetcher(None, OpenerAdapter(opener)), TODAY, ALLOWLIST)
    assert asked == []


def test_the_module_reads_no_files():
    assert "open(" not in Path(__import__("checks.submissions").submissions.__file__).read_text(encoding="utf-8")
