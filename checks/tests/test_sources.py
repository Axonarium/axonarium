"""Source records: built from Crossref and DataCite metadata, filled and refreshed by `checks sources`."""

from datetime import date

from checks.lookups import crossref_work, datacite_record
from checks.sources import source_from_crossref, source_from_datacite

TODAY = date(2026, 10, 3)
HINTIRYAN = "10.1038/s41467-021-22915-5"
WAKEFIELD = "10.1016/s0140-6736(97)11096-0"
PAPERQA2 = "10.48550/arXiv.2409.13740"


def test_crossref_open_paper(fetch):
    assert source_from_crossref(HINTIRYAN, crossref_work(fetch, HINTIRYAN), TODAY) == {
        "id": "doi:10.1038/s41467-021-22915-5",
        "title": "Connectivity characterization of the mouse basolateral amygdalar complex",
        "year": 2021,
        "journal": "Nature Communications",
        "license": "CC-BY-4.0",
        "open_access": True,
        "retracted": False,
    }


def test_crossref_retracted_paper(fetch):
    record = source_from_crossref(WAKEFIELD, crossref_work(fetch, WAKEFIELD), TODAY)
    assert record["retracted"] is True
    assert "license" not in record and "open_access" not in record  # Its only licence is for text mining.


def test_datacite_preprint(fetch):
    record = source_from_datacite(PAPERQA2, datacite_record(fetch, PAPERQA2))
    assert record["id"] == "doi:10.48550/arxiv.2409.13740"
    assert record["license"] == "CC-BY-SA-4.0" and record["open_access"] is True and record["journal"] == "arXiv"
    assert "retracted" not in record


def test_crossref_licence_not_yet_started():
    message = {"license": [{"URL": "https://creativecommons.org/licenses/by/4.0/", "content-version": "vor",
                            "start": {"date-parts": [[2026, 10, 4]]}}]}
    assert "license" not in source_from_crossref("10.5555/x", message, TODAY)


def test_title_markup_stripped():
    message = {"title": ["<i>Mus</i>  musculus\n wiring &amp; more"]}
    assert source_from_crossref("10.5555/x", message, TODAY)["title"] == "Mus musculus wiring & more"
