"""The corpus manifest (sprint 2.2) and the pipeline's ledgers beside it: one CSV row per paper, sorted by key."""

import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
MANIFEST = CORPUS / "manifest.csv"


def read_manifest(path: Path = MANIFEST) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@dataclass
class Ledger:
    """A CSV keyed by paper: what a step decided or did for each paper, with the prompt and model that did it."""

    path: Path
    columns: tuple[str, ...]

    def read(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        with self.path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if tuple(reader.fieldnames or ()) != self.columns:
                raise ValueError(f"{self.path}: columns {reader.fieldnames}, expected {list(self.columns)}")
            return {row["key"]: row for row in reader}

    def update(self, rows: list[dict]) -> None:
        """Add or replace these papers' rows, keeping every other row; the file stays sorted by key."""
        merged = self.read()
        for row in rows:
            unknown = set(row) - set(self.columns)
            if unknown:
                raise ValueError(f"{self.path}: unknown columns {sorted(unknown)}")
            merged[row["key"]] = {column: row.get(column, "") for column in self.columns}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(merged[key] for key in sorted(merged))
