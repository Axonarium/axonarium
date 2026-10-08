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


# How the pipeline avoids reading a paper twice (ADR 0028). A step that has finished a paper never sends it again, whatever
# version of the prompt finished it, unless asked to (`--redo`). A paper whose answers keep failing is set aside after
# MAX_ATTEMPTS model reads. Batch entries no model answered don't count as reads.
MAX_ATTEMPTS = 2
UNANSWERED = {"errored", "expired", "canceled"}


def aliases(paper: dict) -> list[str]:
    """Every key the paper has or could have had: a paper keyed by its PubMed ID that later gains a DOI is the same paper."""
    keys = [paper["key"]] + [f"{prefix}:{paper[column]}" for prefix, column in (("doi", "doi"), ("pubmed", "pmid"), ("pmc", "pmcid"))
                             if paper.get(column)]
    return list(dict.fromkeys(keys))


def recorded(ledger: dict[str, dict], paper: dict) -> dict | None:
    """The paper's row in a ledger, under any of its keys."""
    return next((ledger[key] for key in aliases(paper) if key in ledger), None)


def attempts(previous: dict | None, stop: str | None) -> str:
    """The row's new count of model reads: one more, unless no model answered (`stop` is None when nothing was sent)."""
    before = int((previous or {}).get("attempts") or 0)
    return str(before + (0 if stop is None or stop in UNANSWERED else 1))


def identifier(value: str) -> str:
    """A paper's key from what someone typed: a key, a DOI, a PubMed ID or a PMC ID."""
    value = value.strip().lower()
    if value.startswith(("doi:", "pubmed:", "pmc:", "europepmc:")):
        return value
    if value.startswith("10."):
        return f"doi:{value}"
    if value.startswith("pmc"):
        return f"pmc:{value}"
    return f"pubmed:{value}" if value.isdigit() else value


@dataclass(frozen=True)
class Redo:
    """Papers to send again although the step has finished them: `older` (finished by another version of the prompt), `all`,
    or papers named by key, DOI, PubMed ID or PMC ID. Values may be separated by commas or spaces."""

    values: tuple[str, ...] = ()

    @property
    def names(self) -> set[str]:
        return {identifier(v) for value in self.values for v in value.replace(",", " ").split()} - {"older", "all"}

    @property
    def words(self) -> set[str]:
        return {v.strip().lower() for value in self.values for v in value.replace(",", " ").split()} & {"older", "all"}

    def wants(self, paper: dict, prompt: str | None, prompt_id: str) -> bool:
        """Whether to send this paper again; `prompt` is the version that finished it."""
        if "all" in self.words or ("older" in self.words and prompt is not None and prompt != prompt_id):
            return True
        return bool(self.names & {key.lower() for key in aliases(paper)})


def due(paper: dict, row: dict | None, outcome: str, finished: set[str], prompt_id: str, redo: Redo) -> bool:
    """Whether a step should send this paper: it has no row, its last try failed and it has tries left, or it is asked for again."""
    if row is None:
        return True
    if redo.wants(paper, row.get("prompt"), prompt_id):
        return True
    if row.get(outcome) in finished:
        return False
    return int(row.get("attempts") or 0) < MAX_ATTEMPTS


def set_aside(manifest: list[dict], ledger: dict[str, dict], outcome: str, finished: set[str]) -> list[str]:
    """Papers whose answers failed MAX_ATTEMPTS times: they wait for a --redo."""
    found = []
    for paper in manifest:
        row = recorded(ledger, paper)
        if row and row.get(outcome) not in finished and int(row.get("attempts") or 0) >= MAX_ATTEMPTS:
            found.append(f"{paper['key']}: {row.get(outcome)}")
    return found
