"""Source records: built from Crossref, DataCite or NCBI metadata. Abstracts are never stored (ADR 0005)."""

import html
import re
from datetime import date
from pathlib import Path

import yaml

from checks.findings import Finding
from checks.http import Fetcher, LookupFailed
from checks.identifiers import canonical_source_id, citation_of, source_file_name, source_key, spdx_from_url
from checks.loading import load_tree
from checks.lookups import CROSSREF, DATACITE, arxiv_doi, crossref_work, datacite_record, doi_agency, ncbi_summary, pubmed_ids_for_doi

FIELDS = ("id", "title", "year", "journal", "kind", "license", "open_access", "retracted")
CLAIMS = ("ConnectivityClaim", "HomologyClaim")
RETRACTING = {"retraction", "withdrawal", "removal"}  # Crossref update types that withdraw a paper
TAGS = re.compile(r"<[^>]+>")
# A source's kind (ADR 0015), from each registry's own type: Crossref's type, DataCite's resourceTypeGeneral and
# PubMed's publication types. Anything not listed is "other".
CROSSREF_KINDS = {"journal-article": "journal_article", "dataset": "dataset"}
DATACITE_KINDS = {"JournalArticle": "journal_article", "Preprint": "preprint", "Dataset": "dataset"}
PUBMED_ARTICLES = {"Journal Article", "Review"}
# Preprint servers by the name NCBI gives them (its `source`, lowercased), and the name source records use.
PREPRINT_SERVERS = {"arxiv": "arXiv", "biorxiv": "bioRxiv", "medrxiv": "medRxiv", "res sq": "Research Square"}


def _text(value) -> str | None:
    """Plain text: markup tags removed, entities decoded, whitespace collapsed."""
    if not isinstance(value, str):
        return None
    return " ".join(html.unescape(TAGS.sub("", value)).split()) or None


def _first(values):
    return values[0] if isinstance(values, list) and values else None


def _date(value) -> date | None:
    """A Crossref date ({"date-parts": [[year, month, day]]}); missing month or day count as the first."""
    try:
        parts = value["date-parts"][0]
        return date(parts[0], *(parts[1:3] + [1, 1])[:2])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _record(source_id: str, **fields) -> dict:
    fields["id"] = source_id
    if isinstance(fields.get("license"), str) and fields["license"].startswith("CC"):
        fields["open_access"] = True
    return {k: fields[k] for k in FIELDS if fields.get(k) is not None}


def _crossref_licence(entries, today: date) -> str | None:
    """The version-of-record licence in force: a Creative Commons one as its SPDX ID if any, else the first URL."""
    urls = [e["URL"] for e in entries if isinstance(e, dict) and isinstance(e.get("URL"), str)
            and e.get("content-version") in ("vor", "unspecified")
            and (_date(e.get("start")) or date.max) <= today] if isinstance(entries, list) else []
    return next((spdx for url in urls if (spdx := spdx_from_url(url))), urls[0] if urls else None)


def source_from_crossref(doi: str, message: dict, today: date) -> dict:
    issued = _date(message.get("issued"))
    updates = message.get("updated-by")
    kind = CROSSREF_KINDS.get(message.get("type"), "other")
    journal = _text(_first(message.get("container-title")))
    if message.get("type") == "posted-content" and message.get("subtype") == "preprint":
        kind = "preprint"  # Its server is the posting institution, such as bioRxiv, not the publisher.
        server = _first(message.get("institution"))
        journal = _text(server.get("name")) if isinstance(server, dict) else None
    return _record(
        f"doi:{doi.lower()}",
        title=_text(_first(message.get("title"))),
        year=issued.year if issued else None,
        journal=journal,
        kind=kind,
        license=_crossref_licence(message.get("license"), today),
        retracted=any(isinstance(u, dict) and u.get("type") in RETRACTING for u in updates) if isinstance(updates, list) else False,
    )


def _spdx_case(identifier: str) -> str:
    return identifier.upper() if identifier.lower().startswith("cc") else identifier


def source_from_datacite(doi: str, attributes: dict) -> dict:
    title = _first(attributes.get("titles"))
    container = attributes.get("container") if isinstance(attributes.get("container"), dict) else {}
    publisher = attributes.get("publisher")
    publisher = publisher.get("name") if isinstance(publisher, dict) else publisher
    year = attributes.get("publicationYear")
    rights = _first(attributes.get("rightsList"))
    licence = None
    if isinstance(rights, dict):
        identifier, scheme = rights.get("rightsIdentifier"), rights.get("rightsIdentifierScheme")
        if isinstance(identifier, str) and isinstance(scheme, str) and scheme.upper() == "SPDX":
            licence = _spdx_case(identifier)
        elif isinstance(rights.get("rightsUri"), str):
            licence = spdx_from_url(rights["rightsUri"])
    types = attributes.get("types") if isinstance(attributes.get("types"), dict) else {}
    arxiv = doi.lower().startswith("10.48550/arxiv.")  # arXiv is a preprint server, whatever type it registers
    return _record(
        f"doi:{doi.lower()}",
        title=_text(title.get("title")) if isinstance(title, dict) else None,
        year=int(year) if isinstance(year, int) or (isinstance(year, str) and year.isdigit()) else None,
        journal=_text(container.get("title")) or _text(publisher),
        kind="preprint" if arxiv else DATACITE_KINDS.get(types.get("resourceTypeGeneral"), "other"),
        license=licence,
    )


def _server(summary: dict) -> str | None:
    """The preprint server an NCBI summary's journal is, by the name source records use; None for a journal."""
    source = _text(summary.get("source"))
    return PREPRINT_SERVERS.get(source.lower()) if source else None


def _ncbi(source_id: str, summary: dict, preprint: bool = False) -> dict:
    """Title, year and journal from an NCBI summary (PubMed or PubMed Central). A preprint's journal is its server."""
    year = re.match(r"([0-9]{4})", summary.get("pubdate") or "")
    journal = _text(summary.get("fulljournalname")) or _text(summary.get("source"))
    if preprint:
        journal = _server(summary) or _text(summary.get("source"))
    return dict(title=_text(summary.get("title")), year=int(year[1]) if year else None, journal=journal)


def _pubmed_kind(summary: dict) -> str:
    """A PubMed record's kind, from its publication types: a preprint, a journal article or review, or other."""
    types = summary.get("pubtype") if isinstance(summary.get("pubtype"), list) else []
    if "Preprint" in types:
        return "preprint"
    return "journal_article" if PUBMED_ARTICLES & set(types) else "other"


def pubmed_says_retracted(summary: dict) -> bool:
    """Whether a PubMed summary lists the paper as a "Retracted Publication"."""
    types = summary["pubtype"]
    if not isinstance(types, list):  # An unexpected shape must not read as "not retracted".
        raise TypeError("PubMed's pubtype is not a list")
    return "Retracted Publication" in types


def source_from_pubmed(pmid: str, summary: dict) -> dict:
    kind = _pubmed_kind(summary)
    return _record(f"pubmed:{pmid}", **_ncbi(pmid, summary, kind == "preprint"), kind=kind,
                   retracted=pubmed_says_retracted(summary))


def _pubmed_retracted(fetch: Fetcher, doi: str) -> bool | None:
    """Whether PubMed lists a paper with this DOI as retracted; None if PubMed has no record with it."""
    summaries = [s for pmid in pubmed_ids_for_doi(fetch, doi) if (s := ncbi_summary(fetch, "pubmed", pmid)) is not None]
    return any(pubmed_says_retracted(s) for s in summaries) if summaries else None


def source_from_pmc(pmcid: str, summary: dict) -> dict:
    # PubMed Central has no retraction status or publication types: its records are journal articles, except
    # those from preprint servers.
    preprint = _server(summary) is not None
    return _record(f"pmc:{pmcid}", **_ncbi(pmcid, summary, preprint), kind="preprint" if preprint else "journal_article")


def fetch_source(fetch: Fetcher, source_id: str, today: date) -> dict | None:
    """The source record for a source ID (doi:, pubmed:, pmc: or arxiv:); None if the paper doesn't exist."""
    scheme, _, rest = source_id.partition(":")
    if scheme == "pubmed":
        summary = ncbi_summary(fetch, "pubmed", rest)
        return source_from_pubmed(rest, summary) if summary is not None else None
    if scheme == "pmc":
        summary = ncbi_summary(fetch, "pmc", rest.removeprefix("PMC"))
        return source_from_pmc(rest, summary) if summary is not None else None
    if scheme == "arxiv":
        attributes = datacite_record(fetch, arxiv_doi(rest))
        return source_from_datacite(arxiv_doi(rest), attributes) | {"id": source_id} if attributes is not None else None
    if scheme != "doi":
        raise ValueError(f"unknown source scheme in {source_id!r}")
    record = _doi_record(fetch, rest, today)
    if record is not None and (pubmed := _pubmed_retracted(fetch, rest)) is not None:
        record["retracted"] = record.get("retracted", False) or pubmed  # Crossref misses some retractions PubMed has.
    return record


def _doi_record(fetch: Fetcher, doi: str, today: date) -> dict | None:
    """The record for a DOI from its registration agency; None if the DOI doesn't exist."""
    agency = doi_agency(fetch, doi)
    if agency is None:
        return None
    if agency == "Crossref":
        message = crossref_work(fetch, doi)
        if message is None:
            raise LookupFailed(CROSSREF.format(doi=doi), "doi.org names Crossref, but Crossref has no record")
        return source_from_crossref(doi, message, today)
    if agency == "DataCite":
        attributes = datacite_record(fetch, doi)
        if attributes is None:
            raise LookupFailed(DATACITE.format(doi=doi), "doi.org names DataCite, but DataCite has no record")
        return source_from_datacite(doi, attributes)
    return _record(f"doi:{doi.lower()}", kind="other")  # Other agencies: the DOI exists, and that is all the checks know.


def write_source(path: Path, record: dict) -> None:
    """Write a source record with its fields in the usual order, then `extra`."""
    ordered = {k: record[k] for k in (*FIELDS, "extra") if k in record}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=1000), encoding="utf-8")


def _fetch(fetch: Fetcher, source_id: str, today: date, path: Path) -> tuple[dict | None, list[Finding]]:
    try:
        record = fetch_source(fetch, source_id, today)
    except LookupFailed as error:
        return None, [Finding(str(path), "lookup-failed", f"lookup failed: {error}")]
    except (TypeError, AttributeError, KeyError, ValueError, IndexError) as error:  # A registry answer of an unexpected shape
        return None, [Finding(str(path), "lookup-failed", f"lookup failed: unexpected answer for {source_id} ({type(error).__name__}: {error})")]
    if record is None:
        return None, [Finding(str(path), "unknown-citation", f"{source_id} does not exist")]
    return record, []


def fill_sources(data_dir: Path, fetch: Fetcher, today: date, refresh: bool = False) -> tuple[list[Path], list[Finding]]:
    """Write a record for every cited source key that has none; with refresh, also rewrite records whose metadata changed."""
    records, _ = load_tree(data_dir)
    existing = {r.data["id"].lower(): r for r in records if r.cls == "Source" and isinstance(r.data.get("id"), str)}
    cited: dict[str, Path] = {}
    for record in records:
        if record.cls in CLAIMS and (key := source_key(citation_of(record.data))):
            cited.setdefault(key, record.path)
    written, findings = [], []
    for key, claim_path in sorted(cited.items()):
        if key.lower() in existing:
            continue
        if not canonical_source_id(key):
            findings.append(Finding(str(claim_path), "unknown-citation", f"{key!r} is not in canonical form"))
            continue
        fresh, found = _fetch(fetch, key, today, claim_path)
        findings += found
        if fresh is not None:
            path = data_dir / "sources" / key.partition(":")[0] / source_file_name(fresh["id"])
            write_source(path, fresh)
            written.append(path)
    for _, record in sorted(existing.items()) if refresh else ():
        source_id = record.data["id"]
        if not canonical_source_id(source_id):
            findings.append(Finding(str(record.path), "unknown-citation", f"{source_id!r} is not in canonical form"))
            continue
        fresh, found = _fetch(fetch, source_id, today, record.path)
        findings += found
        if fresh is not None and "extra" in record.data:
            fresh["extra"] = record.data["extra"]
        if fresh is not None and fresh != record.data:
            write_source(record.path, fresh)
            written.append(record.path)
    return written, sorted(findings)
