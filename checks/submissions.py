"""Vetting a paper identifier someone submits as evidence for or against a claim (sprint C.1; plan Part 3.3).

Layer 1 of the community-input defences: accept identifiers, not URLs. A submission is turned into a canonical
DOI, PubMed ID, PubMed Central ID or arXiv ID, or refused; only the registries' own URLs for those identifiers
are understood, never the page behind a link. The canonical ID is then looked up in its registry (it must exist
and not be retracted) and its kind checked against the allowlist (Layer 2, ADR 0015). Nothing here fetches the
paper itself.
"""

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import unquote

from checks.http import Fetcher, LookupFailed
from checks.identifiers import canonical_source_id
from checks.sources import fetch_source
from checks.tree_rules import accepts

MAX_LENGTH = 300
DOI = r"(10\.\d{4,9}/[!-~]+)"
FORMS = [  # (pattern, scheme); each pattern is matched against the whole stripped submission, ignoring case
    (rf"(?:doi:\s*)?{DOI}", "doi"),
    (rf"https?://(?:dx\.)?doi\.org/{DOI}", "doi"),
    (r"https?://(?:www\.)?(?:biorxiv|medrxiv)\.org/content/(10\.1101/(?:\d{4}\.\d{2}\.\d{2}\.)?\d{6,})(?:v\d+)?(?:\.full(?:\.pdf)?|\.abstract)?/?", "doi"),
    (r"(?:pmid:?\s*)?([1-9]\d{0,8})", "pubmed"),
    (r"https?://pubmed\.ncbi\.nlm\.nih\.gov/([1-9]\d{0,8})/?", "pubmed"),
    (r"https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed/([1-9]\d{0,8})/?", "pubmed"),
    (r"https?://(?:www\.)?europepmc\.org/(?:article|abstract)/MED/([1-9]\d{0,8})/?", "pubmed"),
    (r"(?:pmcid:?\s*)?(PMC[1-9]\d*)", "pmc"),
    (r"https?://(?:www\.)?(?:ncbi\.nlm\.nih\.gov/pmc|pmc\.ncbi\.nlm\.nih\.gov)/articles/(PMC[1-9]\d*)/?", "pmc"),
    (r"https?://(?:www\.)?europepmc\.org/(?:article|abstract)/PMC/(PMC[1-9]\d*)/?", "pmc"),
    (r"(?:arxiv:\s*)?(\d{4}\.\d{4,5})(?:v[1-9]\d*)?", "arxiv"),
    (r"https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v[1-9]\d*)?(?:\.pdf)?/?", "arxiv"),
]
COMPILED = [(re.compile(pattern, re.IGNORECASE), scheme) for pattern, scheme in FORMS]


def canonical_identifier(raw: str) -> str | None:
    """The canonical source ID (doi:, pubmed:, pmc: or arxiv:) a submission names, or None if it names none."""
    text = raw.strip() if isinstance(raw, str) else ""
    if not text or len(text) > MAX_LENGTH:
        return None
    for pattern, scheme in COMPILED:  # whitespace is allowed only after a label such as "PMID"
        match = pattern.fullmatch(unquote(text) if scheme == "doi" else text)
        if not match:
            continue
        value = match[1]
        source_id = {"doi": f"doi:{value.lower()}", "pubmed": f"pubmed:{value}", "pmc": f"pmc:{value.upper()}",
                     "arxiv": f"arxiv:{value}"}[scheme]
        return source_id if canonical_source_id(source_id) else None
    return None


@dataclass(frozen=True)
class Vetting:
    status: str  # accepted, malformed, unknown, retracted, not-allowed or lookup-failed
    source_id: str | None = None
    reason: str | None = None
    record: dict | None = None  # the source record, when accepted


def vet(raw: str, fetch: Fetcher, today: date, allowlist: list[dict]) -> Vetting:
    """Whether a submitted identifier names an existing, unretracted paper of a kind the allowlist accepts."""
    source_id = canonical_identifier(raw)
    if source_id is None:
        return Vetting("malformed", reason="not a DOI, PubMed ID, PubMed Central ID or arXiv ID")
    try:
        record = fetch_source(fetch, source_id, today)
    except LookupFailed as error:  # Not the submitter's fault: try again later rather than reject.
        return Vetting("lookup-failed", source_id, str(error))
    except (TypeError, AttributeError, KeyError, ValueError, IndexError) as error:
        return Vetting("lookup-failed", source_id, f"unexpected answer for {source_id} ({type(error).__name__})")
    if record is None:
        return Vetting("unknown", source_id, f"{source_id} does not exist")
    if record.get("retracted") is True:
        return Vetting("retracted", source_id, f"{source_id} is retracted")
    if not accepts(allowlist, record):
        venue = f" from {record['journal']}" if record.get("journal") else ""
        return Vetting("not-allowed", source_id, f"{source_id} is a {record.get('kind')}{venue}, which the allowlist doesn't accept")
    return Vetting("accepted", source_id, record=record)
