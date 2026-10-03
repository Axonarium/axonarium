"""Source records: built from Crossref or DataCite metadata. Abstracts are never stored (ADR 0005)."""

import html
import re
from datetime import date

from checks.http import Fetcher, LookupFailed
from checks.identifiers import spdx_from_url
from checks.lookups import CROSSREF, DATACITE, crossref_work, datacite_record, doi_agency

FIELDS = ("id", "title", "year", "journal", "license", "open_access", "retracted")
RETRACTING = {"retraction", "withdrawal", "removal"}  # Crossref update types that withdraw a paper
TAGS = re.compile(r"<[^>]+>")


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


def _record(doi: str, **fields) -> dict:
    fields["id"] = f"doi:{doi.lower()}"
    if isinstance(fields.get("license"), str) and fields["license"].startswith("CC"):
        fields["open_access"] = True
    return {k: fields[k] for k in FIELDS if fields.get(k) is not None}


def _crossref_licence(entries, today: date) -> str | None:
    """The version-of-record licence in force: a Creative Commons one as its SPDX ID if any, else the first URL."""
    urls = [e["URL"] for e in entries if isinstance(e, dict) and isinstance(e.get("URL"), str)
            and e.get("content-version") in ("vor", "unspecified")
            and (_date(e.get("start")) or today) <= today] if isinstance(entries, list) else []
    return next((spdx for url in urls if (spdx := spdx_from_url(url))), urls[0] if urls else None)


def source_from_crossref(doi: str, message: dict, today: date) -> dict:
    issued = _date(message.get("issued"))
    updates = message.get("updated-by")
    return _record(
        doi,
        title=_text(_first(message.get("title"))),
        year=issued.year if issued else None,
        journal=_text(_first(message.get("container-title"))),
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
    return _record(
        doi,
        title=_text(title.get("title")) if isinstance(title, dict) else None,
        year=int(year) if isinstance(year, int) or (isinstance(year, str) and year.isdigit()) else None,
        journal=_text(container.get("title")) or _text(publisher),
        license=licence,
    )


def fetch_source(fetch: Fetcher, doi: str, today: date) -> dict | None:
    """The source record for a DOI from its registration agency; None if the DOI doesn't exist."""
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
    return _record(doi)  # Other agencies: the DOI exists, and that is all the checks know.
