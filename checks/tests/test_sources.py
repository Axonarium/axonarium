"""Source records: built from Crossref and DataCite metadata, filled and refreshed by `checks sources`."""

import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml

from checks.cli import main, run_files
from checks.lookups import crossref_work, datacite_record
from checks.sources import fill_sources, source_from_crossref, source_from_datacite

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
