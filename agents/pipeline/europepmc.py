"""Europe PMC, read at run time: abstracts for triage and full text for extraction. Neither is committed (ADR 0005,
ADR 0028); full text is cached in .cache/papers, as the eval harness caches it.

Europe PMC serves full text for its open-access subset and for preprints it holds the text of. When it won't serve a
PMC paper, PMC's open data on AWS often does: its open-access and author manuscript datasets, both licensed for text
mining (ADR 0030)."""

import hashlib
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&resultType=core&format=json&pageSize=1"
FULL_TEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{paper_id}/fullTextXML"
PMC_BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com/"
PMC_ID = re.compile(r"^PMC\d+$")
PREPRINT_ID = re.compile(r"^PPR\d+$")
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


def text_id(paper: dict) -> str:
    """The ID a manifest paper's full text is fetched by: its PMC ID, else a preprint's Europe PMC ID (PPR…), else ""."""
    if paper.get("pmcid"):
        return paper["pmcid"]
    source, _, ext_id = (paper.get("europe_pmc") or "").partition(":")
    return ext_id if source == "PPR" and PREPRINT_ID.match(ext_id) else ""


def pmc_open_data(pmcid: str, download: Callable[[str], bytes] = get) -> bytes | None:
    """A paper's JATS full text from PMC's open data on AWS, its newest version, or None if PMC doesn't share it there.
    The bucket holds PMC's open-access and author manuscript datasets; its metadata gives each file's MD5."""
    listing = ET.fromstring(download(f"{PMC_BUCKET}?prefix={pmcid}."))
    keys = [e.text or "" for e in listing.iter() if e.tag.rsplit("}", 1)[-1] == "Key"]
    versions = [int(m.group(1)) for k in keys if (m := re.fullmatch(rf"{pmcid}\.(\d+)/{pmcid}\.\1\.json", k))]
    if not versions:
        return None
    meta = json.loads(download(f"{PMC_BUCKET}{pmcid}.{max(versions)}/{pmcid}.{max(versions)}.json"))
    found = re.fullmatch(r"s3://pmc-oa-opendata/([^?]+)\?md5=([0-9a-f]{32})", meta.get("xml_url") or "")
    if not found:
        return None
    body = download(PMC_BUCKET + found.group(1))
    if hashlib.md5(body).hexdigest() != found.group(2):  # noqa: S324 (a checksum, not security)
        raise ValueError(f"{pmcid}'s XML from PMC's open data doesn't match its MD5")
    return body


def full_text(paper_id: str, download: Callable[[str], bytes] = get, cache: Path = CACHE) -> bytes:
    """A paper's JATS full text by its PMC ID or preprint ID (text_id gives it), from the cache once fetched. A PMC paper
    Europe PMC won't serve is looked for in PMC's open data; if it isn't there either, Europe PMC's error is raised."""
    if not (PMC_ID.match(paper_id) or PREPRINT_ID.match(paper_id)):
        raise ValueError(f"{paper_id!r} is not a PMC ID or a Europe PMC preprint ID")
    cached = cache / f"{paper_id}.xml"
    if not cached.exists():
        try:
            body = download(FULL_TEXT.format(paper_id=paper_id))
        except HTTPError as error:
            body = pmc_open_data(paper_id, download) if PMC_ID.match(paper_id) else None
            if body is None:
                raise error from None
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(body)
    return cached.read_bytes()
