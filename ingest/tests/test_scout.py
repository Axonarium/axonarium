"""The scout (sprint 2.2): saved Europe PMC queries become a deduplicated corpus manifest (ADR 0019)."""

import csv
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from checks.http import Fetcher, LookupFailed
from checks.tests.conftest import OpenerAdapter
from ingest.scout import COLUMNS, main, manifest_rows, read_queries, run_query, scout


def paper(pmid=None, doi=None, pmcid=None, *, source="MED", ppr=None, title="A paper.", year="2020", journal="J Neurosci",
          oa="N", license=None, types=("research-article", "Journal Article"), in_epmc="N", publisher=None) -> dict:
    record = {"id": ppr or pmid, "source": source, "title": title, "pubYear": year, "isOpenAccess": oa, "inEPMC": in_epmc,
              "pubTypeList": {"pubType": list(types)}}
    record |= {k: v for k, v in (("pmid", pmid), ("doi", doi), ("pmcid", pmcid), ("license", license)) if v}
    if journal and source == "MED":
        record["journalInfo"] = {"journal": {"title": journal}}
    if publisher:
        record["bookOrReportDetails"] = {"publisher": publisher}
    return record


def europe_pmc(pages: dict[str, list[list[dict]]], asked: list[str] | None = None):
    """An opener answering Europe PMC searches: each query's pages, chained by cursor marks."""
    def opener(url, headers, timeout):
        if asked is not None:
            asked.append(url)
        params = parse_qs(urlsplit(url).query)
        query, cursor = params["query"][0], params["cursorMark"][0]
        found = pages[query]
        index = 0 if cursor == "*" else int(cursor.removeprefix("page"))
        body = {"hitCount": sum(map(len, found)), "resultList": {"result": found[index] if index < len(found) else []},
                "nextCursorMark": f"page{index + 1}" if index + 1 < len(found) else cursor}
        return 200, {}, json.dumps(body).encode()
    return opener


def fetch(pages, asked=None) -> Fetcher:
    return Fetcher(None, OpenerAdapter(europe_pmc(pages, asked)))


def test_a_query_follows_cursor_marks_to_the_end():
    asked = []
    pages = {"amygdala": [[paper("1"), paper("2")], [paper("3")]]}
    assert [r["pmid"] for r in run_query(fetch(pages, asked), "amygdala")] == ["1", "2", "3"]
    assert len(asked) == 2 and all("resultType=core" in url and "format=json" in url for url in asked)


def test_a_query_that_finds_too_much_is_refused():
    pages = {"brain": [[paper(str(n)) for n in range(3)]]}
    with pytest.raises(LookupFailed, match="3 results"):
        run_query(fetch(pages), "brain", limit=2)


def test_rows_are_deduplicated_across_queries_and_identifiers():
    results = {
        "tracing": [paper("10", doi="10.1/A", pmcid="PMC5", oa="Y", license="cc by", in_epmc="Y"), paper("11")],
        "optogenetics": [paper("10", doi="10.1/a"), paper("12", doi="10.1/b")],
    }
    rows = manifest_rows(results, previous=[], today="2026-10-04")
    assert [r["key"] for r in rows] == ["doi:10.1/a", "doi:10.1/b", "pubmed:11"]
    first = rows[0]
    assert first["queries"] == "optogenetics;tracing" and first["pmcid"] == "PMC5" and first["open_access"] == "true"
    assert first["license"] == "cc by" and first["full_text"] == "true" and first["first_seen"] == "2026-10-04"


def test_preprints_name_their_server_and_kind():
    preprint = paper(doi="10.1101/2020.01.01.000001", source="PPR", ppr="PPR123", journal=None, publisher="bioRxiv",
                     types=("Preprint",))
    [row] = manifest_rows({"q": [preprint]}, previous=[], today="2026-10-04")
    assert row["key"] == "doi:10.1101/2020.01.01.000001" and row["europe_pmc"] == "PPR:PPR123"
    assert row["journal"] == "bioRxiv" and row["types"] == "Preprint"


def test_first_seen_survives_reruns_and_dropped_papers_leave():
    previous = [{**dict.fromkeys(COLUMNS, ""), "key": "pubmed:1", "pmid": "1", "first_seen": "2026-09-01"},
                {**dict.fromkeys(COLUMNS, ""), "key": "pubmed:9", "pmid": "9", "first_seen": "2026-09-01"}]
    rows = manifest_rows({"q": [paper("1"), paper("2")]}, previous=previous, today="2026-10-04")
    assert {r["key"]: r["first_seen"] for r in rows} == {"pubmed:1": "2026-09-01", "pubmed:2": "2026-10-04"}


def test_titles_lose_markup_and_spare_whitespace():
    [row] = manifest_rows({"q": [paper("1", title="<i>Mus</i>  musculus\n amygdala.")]}, previous=[], today="2026-10-04")
    assert row["title"] == "Mus musculus amygdala."


def test_the_projects_queries_are_well_formed():
    queries = read_queries()
    assert len({q["id"] for q in queries}) == len(queries) >= 3
    assert all(q["id"].replace("-", "").isalnum() and q["query"].strip() and q["why"].strip() for q in queries)


def test_scout_writes_a_sorted_manifest_and_keeps_its_history(tmp_path):
    queries = tmp_path / "queries.yaml"
    queries.write_text("queries:\n  - id: tracing\n    why: Test.\n    query: amygdala\n", encoding="utf-8")
    out = tmp_path / "manifest.csv"
    summary = scout(fetch({"amygdala": [[paper("2"), paper("1")]]}), queries, out, today="2026-10-04")
    assert summary == {"tracing": 2, "papers": 2, "new": 2}
    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == list(COLUMNS) and [r["key"] for r in rows] == ["pubmed:1", "pubmed:2"]
    again = scout(fetch({"amygdala": [[paper("1"), paper("3")]]}), queries, out, today="2026-10-05")
    assert again == {"tracing": 2, "papers": 2, "new": 1}


def test_cli_reports_counts(tmp_path, capsys, monkeypatch):
    queries = tmp_path / "queries.yaml"
    queries.write_text("queries:\n  - id: tracing\n    why: Test.\n    query: amygdala\n", encoding="utf-8")
    monkeypatch.setattr("ingest.scout.Fetcher", lambda *a, **k: fetch({"amygdala": [[paper("1")]]}))
    assert main(["--queries", str(queries), "--out", str(tmp_path / "manifest.csv")]) == 0
    assert capsys.readouterr().out.splitlines() == ["tracing: 1 result(s)", "1 paper(s), 1 new"]
