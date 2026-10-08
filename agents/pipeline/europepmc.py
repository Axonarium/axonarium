"""Europe PMC, read at run time: abstracts for triage and open-access full text for extraction. Neither is committed
(ADR 0005, ADR 0028); full text is cached in .cache/papers, as the eval harness caches it."""

import html
import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&resultType=core&format=json&pageSize=1"
FULL_TEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
CACHE = Path(__file__).resolve().parents[2] / ".cache" / "papers"
USER_AGENT = "axonarium-pipeline (https://github.com/axonarium/axonarium; mailto:admin@axonarium.com)"
TAGS = re.compile(r"<[^>]+>")


def get(url: str, attempts: int = 4, pause: float = 2.0) -> bytes:
    """A response body, retried with backoff when Europe PMC is busy or the network drops."""
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as response:  # noqa: S310 (fixed https host)
                return response.read()
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
        except URLError:
            if attempt == attempts - 1:
                raise
        time.sleep(pause * 2**attempt)
    raise AssertionError("unreachable")


def get_json(url: str) -> dict:
    return json.loads(get(url))


def clean(text: str | None) -> str:
    return " ".join(html.unescape(TAGS.sub(" ", text or "")).split())


def abstract(europe_pmc: str, fetch: Callable[[str], dict] = get_json) -> str:
    """A paper's abstract by its Europe PMC ID (such as MED:8742308 or PPR:PPR28619), or "" if it has none."""
    source, _, ext_id = europe_pmc.partition(":")
    if not source or not ext_id:
        raise ValueError(f"{europe_pmc!r} is not a Europe PMC ID such as MED:8742308")
    body = fetch(SEARCH.format(query=quote(f"EXT_ID:{ext_id} AND SRC:{source}", safe="")))
    found = body.get("resultList", {}).get("result", [])
    return clean(found[0].get("abstractText")) if found else ""


def full_text(pmcid: str, download: Callable[[str], bytes] = get, cache: Path = CACHE) -> bytes:
    """A paper's open-access JATS full text by its PMC ID, from the cache once fetched."""
    if not pmcid.startswith("PMC") or not pmcid[3:].isdigit():
        raise ValueError(f"{pmcid!r} is not a PMC ID")
    cached = cache / f"{pmcid}.xml"
    if not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(download(FULL_TEXT.format(pmcid=pmcid)))
    return cached.read_bytes()
