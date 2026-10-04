"""The scout (sprint 2.2, ADR 0019): runs the saved literature searches and writes the corpus manifest.

Command line: `python -m ingest.scout [--queries corpus/queries.yaml] [--out corpus/manifest.csv]`.

Each query in corpus/queries.yaml runs against Europe PMC, which indexes PubMed and preprint servers and says for
each paper whether it is open access, under which licence, and whether Europe PMC holds its full text. The manifest
is one row per paper, deduplicated by DOI, PubMed ID and PubMed Central ID, sorted by key, keeping the date each
paper was first seen so a run shows what is new. It holds identifiers and bibliographic metadata, never abstracts
(ADR 0005).
"""

import argparse
import csv
import html
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

from checks.http import Fetcher, LookupFailed

SEARCH = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&resultType=core"
          "&pageSize=1000&cursorMark={cursor}")
LIMIT = 20_000  # a query finding more than this is too broad to read
ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "corpus" / "queries.yaml"
MANIFEST = ROOT / "corpus" / "manifest.csv"
COLUMNS = ("key", "doi", "pmid", "pmcid", "europe_pmc", "title", "year", "journal", "types", "open_access", "license",
           "full_text", "queries", "first_seen")
TAGS = re.compile(r"<[^>]+>")


def read_queries(path: Path = QUERIES) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["queries"]


def run_query(fetch: Fetcher, query: str, limit: int = LIMIT) -> list[dict]:
    """Every result of one Europe PMC search, a page of 1,000 at a time, following its cursor marks."""
    results, cursor = [], "*"
    while True:
        url = SEARCH.format(query=quote(" ".join(query.split()), safe=""), cursor=quote(cursor, safe=""))
        body = fetch.get_json(url)
        try:
            hits, page, following = body["hitCount"], body["resultList"]["result"], body.get("nextCursorMark")
        except (KeyError, TypeError):
            raise LookupFailed(url, "unexpected answer from Europe PMC") from None
        if hits > limit:
            raise LookupFailed(url, f"the query finds {hits} results, more than {limit}; narrow it")
        results += page
        if not page or not following or following == cursor:
            return results
        cursor = following


def _text(value) -> str:
    return " ".join(html.unescape(TAGS.sub("", value)).split()) if isinstance(value, str) else ""


def _journal(result: dict) -> str:
    info = result.get("journalInfo") or {}
    title = (info.get("journal") or {}).get("title")
    return _text(title or (result.get("bookOrReportDetails") or {}).get("publisher"))


def _row(result: dict) -> dict:
    doi = (result.get("doi") or "").lower()
    pmid, pmcid = result.get("pmid") or "", result.get("pmcid") or ""
    ids = (f"doi:{doi}" if doi else ""), (f"pubmed:{pmid}" if pmid else ""), (f"pmc:{pmcid}" if pmcid else "")
    key = next((i for i in ids if i), f"europepmc:{result.get('source')}:{result.get('id')}")
    return {"key": key, "doi": doi, "pmid": pmid, "pmcid": pmcid, "europe_pmc": f"{result.get('source')}:{result.get('id')}",
            "title": _text(result.get("title")), "year": str(result.get("pubYear") or ""), "journal": _journal(result),
            "types": ";".join(sorted(set((result.get("pubTypeList") or {}).get("pubType") or []))),
            "open_access": str(result.get("isOpenAccess") == "Y").lower(), "license": result.get("license") or "",
            "full_text": str(result.get("inEPMC") == "Y").lower()}


def manifest_rows(results: dict[str, list[dict]], previous: list[dict], today: str) -> list[dict]:
    """One row per paper found by any query, merged across queries by shared identifiers, sorted by key."""
    papers: list[dict] = []
    by_id: dict[str, dict] = {}
    for query_id, found in sorted(results.items()):
        for result in found:
            row = _row(result)
            ids = [f"{k}:{row[k]}" for k in ("doi", "pmid", "pmcid") if row[k]] or [row["key"]]
            known = next((by_id[i] for i in ids if i in by_id), None)
            if known is None:
                known = row | {"queries": set()}
                papers.append(known)
            else:
                for field, value in row.items():  # fill gaps from another record of the same paper; true wins
                    if value and (not known[field] or known[field] == "false"):
                        known[field] = value
            known["queries"].add(query_id)
            for i in ids:
                by_id[i] = known
    seen = {row["key"]: row["first_seen"] for row in previous}
    rows = [{**p, "queries": ";".join(sorted(p["queries"])), "first_seen": seen.get(p["key"]) or today} for p in papers]
    return sorted(rows, key=lambda row: row["key"])


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def scout(fetch: Fetcher, queries: Path, out: Path, today: str | None = None) -> dict[str, int]:
    """Run every saved query and rewrite the manifest; the results per query, papers, and papers new today."""
    today = today or date.today().isoformat()
    results = {q["id"]: run_query(fetch, q["query"]) for q in read_queries(queries)}
    previous = _read(out)
    rows = manifest_rows(results, previous, today)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    known = {row["key"] for row in previous}
    return {**{q: len(found) for q, found in results.items()}, "papers": len(rows),
            "new": sum(row["key"] not in known for row in rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest.scout", description="Run the saved literature searches.")
    parser.add_argument("--queries", type=Path, default=QUERIES, help="the saved queries (default: corpus/queries.yaml)")
    parser.add_argument("--out", type=Path, default=MANIFEST, help="the manifest to write (default: corpus/manifest.csv)")
    args = parser.parse_args(argv)
    try:
        summary = scout(Fetcher(None), args.queries, args.out)
    except LookupFailed as error:
        print(f"the scout stopped: {error}")
        return 1
    papers, new = summary.pop("papers"), summary.pop("new")
    for query_id, count in summary.items():
        print(f"{query_id}: {count} result(s)")
    print(f"{papers} paper(s), {new} new")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
