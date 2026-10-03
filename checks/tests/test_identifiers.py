"""Pure helpers: CURIEs in a record, source file names and licences."""

import pytest

from checks.identifiers import curies_in, is_open_licence, source_file_name, source_key, spdx_from_url


@pytest.mark.parametrize("source_id, name", [
    ("doi:10.1038/s41467-021-22915-5", "doi_10.1038_s41467-021-22915-5.yaml"),
    ("doi:10.1016/s0140-6736(97)11096-0", "doi_10.1016_s0140-6736(97)11096-0.yaml"),
    ("doi:10.1002/(sici)1096-9861(19960101)364:1<1::aid-cne1>3.0.co;2-#",
     "doi_10.1002_(sici)1096-9861(19960101)364%3A1%3C1%3A%3Aaid-cne1%3E3.0.co%3B2-%23.yaml"),
    ("doi:10.5061/dryad.a_b", "doi_10.5061_dryad.a%5Fb.yaml"),
    ("pubmed:34001873", "pubmed_34001873.yaml"),
    ("pmc:PMC8129205", "pmc_PMC8129205.yaml"),
    ("arxiv:2409.13740v2", "arxiv_2409.13740v2.yaml"),
])
def test_source_file_name(source_id, name):
    assert source_file_name(source_id) == name


@pytest.mark.parametrize("url, spdx", [
    ("https://creativecommons.org/licenses/by/4.0", "CC-BY-4.0"),
    ("http://creativecommons.org/licenses/by-nc-nd/4.0/", "CC-BY-NC-ND-4.0"),
    ("https://creativecommons.org/licenses/by-sa/4.0/legalcode", "CC-BY-SA-4.0"),
    ("https://www.creativecommons.org/licenses/by/3.0/igo/", "CC-BY-3.0-IGO"),
    ("https://creativecommons.org/publicdomain/zero/1.0/", "CC0-1.0"),
    ("https://creativecommons.org/licenses/by/4.0/deed.en", "CC-BY-4.0"),
    ("https://www.elsevier.com/tdm/userlicense/1.0/", None),
])
def test_spdx_from_url(url, spdx):
    assert spdx_from_url(url) == spdx


@pytest.mark.parametrize("spdx, is_open", [
    ("CC0-1.0", True),
    ("CC-BY-4.0", True),
    ("CC-BY-2.5", True),
    ("CC-BY-3.0-IGO", True),
    ("CC-BY-SA-4.0", False),
    ("CC-BY-NC-4.0", False),
    ("CC-BY-ND-4.0", False),
    ("https://www.elsevier.com/tdm/userlicense/1.0/", False),
    (None, False),
])
def test_is_open_licence(spdx, is_open):
    assert is_open_licence(spdx) is is_open


def test_curies_in_skips_extra():
    claim = {
        "subject": {"type": "region", "id": "MBA:295", "atlas": "allen-mouse-ccf-2017"},
        "species": "NCBITaxon:10090",
        "paraphrase": "MBA:295 and more",
        "extra": {"lab.ref": "UBERON:0002883"},
    }
    assert curies_in(claim) == {"MBA:295", "NCBITaxon:10090"}


@pytest.mark.parametrize("cited, key", [
    ({"doi": "10.1038/S41467-021-22915-5", "pmid": "34001873", "arxiv": "2409.13740"}, "doi:10.1038/s41467-021-22915-5"),
    ({"pmid": "34001873", "pmcid": "PMC8129205"}, "pubmed:34001873"),
    ({"pmcid": "PMC8129205", "arxiv": "2409.13740"}, "pmc:PMC8129205"),
    ({"arxiv": "2409.13740v2", "locator": "Fig. 1"}, "arxiv:2409.13740"),
    ({"locator": "Fig. 1"}, None),
])
def test_source_key(cited, key):
    assert source_key(cited) == key
