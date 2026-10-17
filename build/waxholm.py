"""The rat in 3D (ADR 0034, "Rat in 3D"): the Waxholm rat atlas structure that draws each UBERON term rat claims name.

UBERON has no bridge to Waxholm, so build/waxholm.yaml is one, kept by hand: each row pairs a Waxholm structure with
the UBERON term for it. A term is drawn on the structure of the most specific row whose term it is or falls under
(is-a or part-of, as OLS computes it, as for modules). Waxholm v4 has a single amygdaloid area, so the amygdala's
nuclei share its mesh. A term no row covers stays in the network view.
"""

from collections import Counter
from pathlib import Path

import yaml

from checks.findings import Record

ATLAS = "waxholm-sd-rat-v4"
RAT = "NCBITaxon:10116"
BRIDGE = Path(__file__).with_name("waxholm.yaml")


def read_bridge(path: Path = BRIDGE) -> list[dict]:
    """The bridge's rows, in the file's order: a Waxholm `structure` ID, a UBERON `term` and UBERON's `label` for it."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))["bridge"]


def rat_terms(records: list[Record]) -> Counter:
    """The UBERON terms rat claims name, with how many claim ends name each."""
    named: Counter = Counter()
    for record in records:
        if record.cls != "ConnectivityClaim" or record.data.get("species") != RAT:
            continue
        for end in (record.data["subject"], record.data["object"]):
            if end.get("type") == "region" and end["id"].startswith("UBERON:"):
                named[end["id"]] += 1
    return named


def problems(bridge: list[dict], structures: dict, terms: dict[str, dict[str, str]]) -> list[str]:
    """What is wrong with the bridge: a structure the pinned atlas lacks, a term OLS doesn't know, or a term listed
    twice. `terms` maps each row's term to the terms under it (ingest.atlases.descendant_terms)."""
    found = []
    for row in bridge:
        if row["structure"] not in structures:
            found.append(f"build/waxholm.yaml: Waxholm has no structure {row['structure']} (for {row['label']})")
        if not terms.get(row["term"]):
            found.append(f"build/waxholm.yaml: OLS doesn't know {row['term']} ({row['label']})")
    for term, count in Counter(row["term"] for row in bridge).items():
        if count > 1:
            found.append(f"build/waxholm.yaml: {term} is listed {count} times")
    return found


def relabelled(bridge: list[dict], terms: dict[str, dict[str, str]]) -> list[str]:
    """Rows whose term UBERON now labels differently, a sign the term may have changed meaning: worth a look, but
    not worth stopping a deploy for."""
    return [f"build/waxholm.yaml: UBERON now labels {row['term']} {terms[row['term']][row['term']]!r}, not "
            f"{row['label']!r}" for row in bridge
            if terms.get(row["term"], {}).get(row["term"]) not in (None, row["label"])]


def resolve(named: list[str], bridge: list[dict], terms: dict[str, dict[str, str]]) -> dict[str, dict]:
    """Per named term that a row covers, the row that draws it: the most specific (the fewest terms under it), and of
    equally specific rows the first in the file."""
    drawn = {}
    for term in named:
        covering = [row for row in bridge if term == row["term"] or term in terms.get(row["term"], {})]
        if covering:
            drawn[term] = min(covering, key=lambda row: len(terms.get(row["term"], {})))  # min keeps the first of ties
    return drawn
