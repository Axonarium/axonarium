"""Source records: built from Crossref and DataCite metadata, filled and refreshed by `checks sources`."""

import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml

from checks.cli import main, run_files
from checks.http import Fetcher
from checks.lookups import crossref_work, datacite_record
from checks.sources import fetch_source, fill_sources, source_from_crossref, source_from_datacite, source_from_pubmed

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


HINTIRYAN_FILE = Path("sources", "doi", "doi_10.1038_s41467-021-22915-5.yaml")
WAKEFIELD_FILE = Path("sources", "doi", "doi_10.1016_s0140-6736(97)11096-0.yaml")


@pytest.fixture
def tree(tmp_path) -> Path:
    data = tmp_path / "data"
    shutil.copytree(Path(__file__).parent / "fixtures" / "online" / "valid", data)
    return data


def test_fill_writes_missing_record(tree, fetch):
    expected = (tree / HINTIRYAN_FILE).read_text(encoding="utf-8")
    (tree / HINTIRYAN_FILE).unlink()
    written, findings = fill_sources(tree, fetch, TODAY)
    assert (written, findings) == ([tree / HINTIRYAN_FILE], [])
    assert (tree / HINTIRYAN_FILE).read_text(encoding="utf-8") == expected
    assert run_files(tree) == []


def test_fill_leaves_existing_records(tree, fetch):
    assert fill_sources(tree, fetch, TODAY) == ([], [])
    assert fetch.requested == []


def test_fill_unknown_doi(tree, fetch):
    claim = tree / "claims" / "examples" / "clm-9dd2wps80g.yaml"
    claim.write_text(claim.read_text(encoding="utf-8").replace(HINTIRYAN, "10.5555/axonarium.missing.001"), encoding="utf-8")
    written, findings = fill_sources(tree, fetch, TODAY)
    assert written == [] and [(f.path, f.rule) for f in findings] == [(str(claim), "unknown-citation")]


def test_refresh_updates_and_keeps_extra(tree, fetch):
    stale = {"id": f"doi:{WAKEFIELD}", "title": "Old title", "year": 1998, "retracted": False, "extra": {"lab.note": "kept"}}
    (tree / WAKEFIELD_FILE).write_text(yaml.safe_dump(stale, sort_keys=False), encoding="utf-8")
    hintiryan_before = (tree / HINTIRYAN_FILE).stat().st_mtime_ns
    written, findings = fill_sources(tree, fetch, TODAY, refresh=True)
    assert (written, findings) == ([tree / WAKEFIELD_FILE], [])
    refreshed = yaml.safe_load((tree / WAKEFIELD_FILE).read_text(encoding="utf-8"))
    assert refreshed["retracted"] is True and refreshed["extra"] == {"lab.note": "kept"}
    assert list(refreshed) == ["id", "title", "year", "journal", "retracted", "extra"]
    assert (tree / HINTIRYAN_FILE).stat().st_mtime_ns == hintiryan_before


def test_cli_sources(tree, replay, tmp_path, capsys):
    (tree / HINTIRYAN_FILE).unlink()
    assert main(["sources", "--data", str(tree), "--cache", str(tmp_path / "cache")], opener=replay) == 0
    assert capsys.readouterr().out.splitlines() == [f"wrote {tree / HINTIRYAN_FILE}"]


def test_licence_without_start_date_not_counted():
    message = {"license": [{"URL": "https://creativecommons.org/licenses/by/4.0/", "content-version": "vor"}]}
    assert "license" not in source_from_crossref("10.5555/x", message, TODAY)


def test_fill_reports_odd_registry_answer(tree, replay):
    (tree / HINTIRYAN_FILE).unlink()
    url = "https://api.crossref.org/works/10.1038/s41467-021-22915-5"

    def opener(asked, headers, timeout):
        return (200, {}, b'{"message": {"updated-by": [{"type": ["retraction"]}]}}') if asked == url else replay(asked, headers, timeout)

    written, findings = fill_sources(tree, Fetcher(None, opener, sleep=lambda seconds: None), TODAY)
    assert written == [] and [f.rule for f in findings] == ["lookup-failed"]


def test_fill_skips_non_canonical_doi(tree, fetch):
    (tree / HINTIRYAN_FILE).unlink()
    claim = tree / "claims" / "examples" / "clm-9dd2wps80g.yaml"
    claim.write_text(claim.read_text(encoding="utf-8").replace(f"doi: {HINTIRYAN}", f'doi: "{HINTIRYAN}\\n"'), encoding="utf-8")
    written, findings = fill_sources(tree, fetch, TODAY)
    assert written == [] and [f.rule for f in findings] == ["unknown-citation"] and fetch.requested == []


def test_cli_refresh_ignores_cached_answers(tree, replay, tmp_path):
    # A local run warmed the cache before the paper was retracted; --refresh must ask again.
    cache, crossref = tmp_path / "cache", "https://api.crossref.org/works/10.1016/s0140-6736%2897%2911096-0"

    def before_retraction(url, headers, timeout):
        return (200, {}, b'{"message": {"title": ["Old"], "updated-by": []}}') if url == crossref else replay(url, headers, timeout)

    Fetcher(cache, before_retraction, sleep=lambda seconds: None).get_json(crossref)
    stale = {"id": f"doi:{WAKEFIELD}", "title": "Old", "retracted": False}
    (tree / WAKEFIELD_FILE).write_text(yaml.safe_dump(stale, sort_keys=False), encoding="utf-8")
    assert main(["sources", "--refresh", "--data", str(tree), "--cache", str(cache)], opener=replay) == 0
    assert yaml.safe_load((tree / WAKEFIELD_FILE).read_text(encoding="utf-8"))["retracted"] is True


ARXIV_FILE = Path("sources", "arxiv", "arxiv_2409.13740.yaml")
PUBMED_FILE = Path("sources", "pubmed", "pubmed_1023575.yaml")


def test_pubmed_record(fetch):
    record = fetch_source(fetch, "pubmed:1023575", TODAY)
    assert record["id"] == "pubmed:1023575" and record["year"] == 1976 and record["retracted"] is False
    assert record["title"] == "Olfactory and temporal projections to the amygdala." and "license" not in record


def test_pubmed_retracted_record(fetch):
    assert fetch_source(fetch, "pubmed:11134581", TODAY)["retracted"] is True


def test_pmc_record(fetch):
    record = fetch_source(fetch, "pmc:PMC8129205", TODAY)
    assert record["id"] == "pmc:PMC8129205" and record["year"] == 2021 and record["journal"]
    assert "retracted" not in record and "license" not in record


def test_arxiv_record(fetch):
    record = fetch_source(fetch, "arxiv:2409.13740", TODAY)
    assert record["id"] == "arxiv:2409.13740" and record["license"] == "CC-BY-SA-4.0" and "retracted" not in record


def test_pubmed_odd_pubdate():
    record = source_from_pubmed("1", {"title": "T", "pubdate": "", "pubtype": ["Journal Article"]})
    assert record == {"id": "pubmed:1", "title": "T", "retracted": False}


def pmid_only_claim(data: Path, pmid: str) -> Path:
    text = (data / "claims" / "examples" / "clm-9dd2wps80g.yaml").read_text(encoding="utf-8")
    text = text.replace("clm-9dd2wps80g", "clm-2w33dsbbr3").replace(f"  doi: {HINTIRYAN}\n", "")
    text = text.replace('  pmid: "34001873"\n', f'  pmid: "{pmid}"\n').replace("  pmcid: PMC8129205\n", "")
    path = data / "claims" / "examples" / "clm-2w33dsbbr3.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_fill_writes_pubmed_and_arxiv_records(tree, fetch):
    pmid_only_claim(tree, "1023575")
    (tree / PUBMED_FILE).unlink(missing_ok=True)
    expected_arxiv = (tree / ARXIV_FILE).read_text(encoding="utf-8")
    (tree / ARXIV_FILE).unlink()
    written, findings = fill_sources(tree, fetch, TODAY)
    assert (sorted(written), findings) == (sorted([tree / ARXIV_FILE, tree / PUBMED_FILE]), [])
    assert (tree / ARXIV_FILE).read_text(encoding="utf-8") == expected_arxiv
    assert yaml.safe_load((tree / PUBMED_FILE).read_text(encoding="utf-8"))["retracted"] is False
    assert run_files(tree) == []


def test_fill_unknown_pmid(tree, fetch):
    claim = pmid_only_claim(tree, "99999999999")
    written, findings = fill_sources(tree, fetch, TODAY)
    assert [(f.path, f.rule) for f in findings] == [(str(claim), "unknown-citation")] and tree / PUBMED_FILE not in written


def test_refresh_mixed_schemes(tree, fetch):
    pmid_only_claim(tree, "1023575")
    fill_sources(tree, fetch, TODAY)
    stale = yaml.safe_load((tree / PUBMED_FILE).read_text(encoding="utf-8")) | {"retracted": True}
    (tree / PUBMED_FILE).write_text(yaml.safe_dump(stale, sort_keys=False), encoding="utf-8")
    written, findings = fill_sources(tree, fetch, TODAY, refresh=True)
    assert (written, findings) == ([tree / PUBMED_FILE], [])
