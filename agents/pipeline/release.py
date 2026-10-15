"""Papers the hidden-text screen flagged that the maintainer has released to a model after reading every finding
(ADR 0033). `corpus/released.csv` names each by key and by its findings' digest, as a run's report prints them, so a
paper whose flagged text changes is held again. Only the maintainer adds rows: the file is code-owned."""

import csv
from pathlib import Path

from pipeline.corpus import CORPUS
from screen import Screened

RELEASED = CORPUS / "released.csv"
COLUMNS = ("key", "findings", "date", "note")


def read(path: Path | None = None) -> dict[str, str]:
    """Released paper keys, lowercased, and the findings digest each was released for."""
    path = path or RELEASED
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        return {row["key"].strip().lower(): row["findings"].strip() for row in csv.DictReader(file)}


def released(paper: dict, screened: Screened, path: Path | None = None) -> bool:
    """Whether a flagged paper may go to a model: the maintainer released it, for exactly these findings."""
    return screened.flagged and read(path).get(paper["key"].lower()) == screened.digest
