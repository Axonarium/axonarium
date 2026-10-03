"""Identifiers in records, the file names of source records, and licences."""

import re

CURIE = re.compile(r"^(UBERON|CL|NCBITaxon|MBA|HBA):\d+$")
SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.()-")
CC_LICENCE = re.compile(
    r"^https?://(www\.)?creativecommons\.org/"
    r"(licenses/(?P<code>by(-nc)?(-nd)?(-sa)?)/(?P<version>\d\.\d)(/(?P<jurisdiction>(?!legalcode|deed)[a-z]{2,}))?"
    r"|publicdomain/zero/(?P<zero>1\.0))"
    r"(/(legalcode(\.[a-z-]+)?|deed\.[a-z-]+))?/?$",
    re.IGNORECASE,
)
OPEN_LICENCE = re.compile(r"^(CC0-1\.0|CC-BY-\d\.\d(-[A-Z]+)?)$")
# The only forms the online checks look up: ASCII, no surrounding whitespace, no leading zeros.
CANONICAL = {
    "curie": re.compile(r"(UBERON|CL|NCBITaxon|MBA|HBA):[0-9]+"),
    "doi": re.compile(r"10\.[0-9]{4,9}/[!-~]+"),
    "pmid": re.compile(r"[1-9][0-9]*"),
    "pmcid": re.compile(r"PMC[1-9][0-9]*"),
    "arxiv": re.compile(r"[0-9]{4}\.[0-9]{4,5}(v[1-9][0-9]*)?"),
}


def curies_in(value) -> set[str]:
    """Every string that is exactly an ontology or atlas CURIE, at any depth, outside `extra`."""
    if isinstance(value, str):
        return {value} if CURIE.match(value) else set()
    if isinstance(value, dict):
        return set().union(*(curies_in(v) for k, v in value.items() if k != "extra"))
    if isinstance(value, list):
        return set().union(*(curies_in(v) for v in value))
    return set()


def source_file_name(source_id: str) -> str:
    """The file name of a source record: the scheme's `:` and every `/` as `_`, other unsafe characters %-encoded."""
    scheme, rest = source_id.split(":", 1)
    escaped = "".join(
        c if c in SAFE else "_" if c == "/" else "".join(f"%{byte:02X}" for byte in c.encode("utf-8"))
        for c in rest
    )
    return f"{scheme}_{escaped}.yaml"


def spdx_from_url(url: str) -> str | None:
    """The SPDX ID of a Creative Commons licence URL; None for any other URL."""
    match = CC_LICENCE.match(url.strip())
    if not match:
        return None
    if match["zero"]:
        return "CC0-1.0"
    spdx = f"CC-{match['code'].upper()}-{match['version']}"
    return f"{spdx}-{match['jurisdiction'].upper()}" if match["jurisdiction"] else spdx


def is_open_licence(spdx: str | None) -> bool:
    """Whether verbatim excerpts may be taken from a source under this licence: CC0 or CC BY, nothing stricter."""
    return isinstance(spdx, str) and bool(OPEN_LICENCE.match(spdx))


def canonical(kind: str, value: str) -> bool:
    """Whether an identifier is in the exact form its registry is asked for (see CANONICAL)."""
    return bool(CANONICAL[kind].fullmatch(value))


def source_key(cited: dict[str, str]) -> str | None:
    """The ID of the source record a citation needs: its DOI, else PubMed ID, else PMC ID, else arXiv ID (no version)."""
    if cited.get("doi"):
        return f"doi:{cited['doi'].lower()}"
    if cited.get("pmid"):
        return f"pubmed:{cited['pmid']}"
    if cited.get("pmcid"):
        return f"pmc:{cited['pmcid']}"
    if cited.get("arxiv"):
        return f"arxiv:{re.sub(r'v[0-9]+$', '', cited['arxiv'])}"
    return None


def citation_of(data: dict) -> dict[str, str]:
    """A claim's citation identifiers and locator that are strings; empty if it has no citation mapping."""
    source = data.get("source")
    return {k: v for k, v in source.items() if isinstance(v, str)} if isinstance(source, dict) else {}
