"""What the checks produce, and what they check."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class Finding:
    """One problem in one file, printed as `<path>: <rule-id>: <message>`."""

    path: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.rule}: {self.message}"


@dataclass(frozen=True)
class Record:
    """One data file: where it is, which schema class its folder implies, and its content."""

    path: Path
    cls: str
    data: dict
