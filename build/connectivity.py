"""Claims made at build time from external sources (ADR 0010), checked like committed claims before they're used."""

from collections.abc import Callable
from pathlib import Path

from checks.file_rules import check_file
from checks.findings import Finding, Record
from checks.tree_rules import check_tree

FOLDER = Path("allen-connectivity")  # Where generated claims say they come from, in findings.


def amygdala_structures(rows: list[dict]) -> list[int]:
    """The Allen structure IDs of the amygdala regions and all their subdivisions, from an atlas's region rows."""
    children: dict[str | None, list[str]] = {}
    for row in rows:
        children.setdefault(row["parent"], []).append(row["id"])
    found, stack = set(), [row["id"] for row in rows if row["amygdala"]]
    while stack:
        region = stack.pop()
        if region not in found:
            found.add(region)
            stack.extend(children.get(region, []))
    return sorted(int(region.split(":")[1]) for region in found)


def allen_records(loaded: dict[str, list[dict]], loader: Callable) -> list[Record]:
    """Allen connectivity claims for every loaded atlas with MBA regions (the Allen mouse atlas), as records."""
    records = []
    for atlas, rows in loaded.items():
        if not rows or not rows[0]["id"].startswith("MBA:"):
            continue
        acronyms = {int(row["id"].split(":")[1]): row["acronym"] for row in rows}
        for claim in loader(atlas, amygdala_structures(rows), acronyms):
            records.append(Record(FOLDER / f"{claim['id']}.yaml", "ConnectivityClaim", claim))
    return records


def check_generated(committed: list[Record], generated: list[Record]) -> list[Finding]:
    """The per-file rules for each generated claim, and the cross-file rules over everything."""
    findings = [finding for record in generated for finding in check_file(record)]
    return sorted(findings + check_tree(committed + generated))
