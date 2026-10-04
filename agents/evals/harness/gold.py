"""A gold set on disk: its manifest, its papers, each paper's text and its gold claims.

    <gold set>/gold.yaml         version, frozen (date), curators, notes
    <gold set>/papers/<name>.yaml
        source: {doi: ..., pmid: ..., pmcid: ...}
        text: {file: texts/<name>.txt}    # committed: synthetic or CC BY/CC0 text only (ADR 0005)
           or {jats: texts/<name>.xml}    # committed JATS, likewise
           or {europe_pmc: PMC1234567}    # open-access full text, fetched at run time and cached, never committed
        claims: [GoldClaim, ...]          # every claim the paper makes, absent results included

Every text passes the hidden-text screen (sprint C.5) before a model may read it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from evals.harness.models import GoldClaim
from screen import Screened, screen_jats, screen_text
from screen.injection import Classifier

FULL_TEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
CACHE = Path(__file__).resolve().parents[3] / ".cache" / "papers"
USER_AGENT = "axonarium-evals (https://github.com/axonarium/axonarium; mailto:admin@axonarium.com)"


@dataclass(frozen=True)
class Paper:
    name: str
    source: dict
    text_spec: dict
    claims: list[GoldClaim]


@dataclass(frozen=True)
class GoldSet:
    path: Path
    version: str
    frozen: str | None
    papers: list[Paper]


def load(path: Path) -> GoldSet:
    manifest = yaml.safe_load((path / "gold.yaml").read_text(encoding="utf-8"))
    papers = []
    for file in sorted((path / "papers").glob("*.yaml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        unknown = set(data) - {"source", "text", "claims"}
        if unknown:
            raise ValueError(f"{file}: unknown keys {sorted(unknown)}")
        papers.append(Paper(file.stem, data["source"], data["text"], [GoldClaim.model_validate(c) for c in data["claims"]]))
    if not papers:
        raise ValueError(f"{path}: no papers in papers/")
    return GoldSet(path, str(manifest["version"]), manifest.get("frozen"), papers)


def _download(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as response:  # noqa: S310 (fixed https URL)
        return response.read()


def text(gold: GoldSet, paper: Paper, classify: Classifier, download: Callable[[str], bytes] = _download,
         cache: Path = CACHE) -> Screened:
    """The paper's screened text, from its committed file or Europe PMC's open-access full text (cached as fetched)."""
    if "file" in paper.text_spec:
        return screen_text((gold.path / paper.text_spec["file"]).read_text(encoding="utf-8"), classify)
    if "jats" in paper.text_spec:
        return screen_jats((gold.path / paper.text_spec["jats"]).read_bytes(), classify)
    pmcid = paper.text_spec["europe_pmc"]
    cached = cache / f"{pmcid}.xml"
    if not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(download(FULL_TEXT.format(pmcid=pmcid)))
    return screen_jats(cached.read_bytes(), classify)
