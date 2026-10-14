"""A gold set on disk: its manifest, its papers, each paper's text and its gold claims.

    <gold set>/gold.yaml         version, frozen (date), curators, notes
    <gold set>/papers/<name>.yaml
        source: {doi: ..., pmid: ..., pmcid: ...}
        text: {file: texts/<name>.txt}    # committed: synthetic or CC BY/CC0 text only (ADR 0005)
           or {jats: texts/<name>.xml}    # committed JATS, likewise
           or {europe_pmc: PMC1234567}    # open-access full text, fetched at run time and cached, never committed
        claims: [GoldClaim, ...]          # every claim the paper makes, absent results included

Every text passes the hidden-text screen (sprint C.5) before a model may read it. JATS papers are cut to the parts
that hold claims, and Europe PMC's text is fetched and cached, exactly as the pipeline reads them (sprint 0.6a), so a
gold score predicts a pipeline run. A plain-text file is read whole: it has no sections to cut.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from evals.harness.models import GoldClaim
from pipeline import europepmc, sections
from screen import Screened, screen_jats, screen_text
from screen.injection import Classifier


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


def text(gold: GoldSet, paper: Paper, classify: Classifier, download: Callable[[str], bytes] = europepmc.get,
         cache: Path = europepmc.CACHE) -> Screened:
    """The paper's screened text, from its committed file or Europe PMC's open-access full text (cached as fetched,
    in the pipeline's cache); JATS pruned as the pipeline prunes it."""
    if "file" in paper.text_spec:
        return screen_text((gold.path / paper.text_spec["file"]).read_text(encoding="utf-8"), classify)
    if "jats" in paper.text_spec:
        xml = (gold.path / paper.text_spec["jats"]).read_bytes()
    else:
        xml = europepmc.full_text(paper.text_spec["europe_pmc"], download, cache)
    return screen_jats(xml, classify, prune=sections.prune)
