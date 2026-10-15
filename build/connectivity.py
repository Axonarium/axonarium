"""Claims made at build time from external sources (ADR 0010), checked like committed claims before they're used."""

from collections.abc import Callable
from pathlib import Path

from checks.file_rules import check_file
from checks.findings import Finding, Record
from checks.tree_rules import check_tree
from ingest.modules import structures

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


def amygdala_regions(regions: list[dict]) -> set[str]:
    """The IDs of the amygdala regions and all their subdivisions, in every atlas among these region rows."""
    by_atlas: dict[str, list[dict]] = {}
    for row in regions:
        by_atlas.setdefault(row["atlas"], []).append(row)
    found = set()
    for rows in by_atlas.values():
        prefix = rows[0]["id"].split(":")[0]
        found |= {f"{prefix}:{n}" for n in amygdala_structures(rows)}
    return found


def module_regions(regions: list[dict]) -> set[str]:
    """The IDs of every module's regions, subdivisions included, among these region rows (after
    ingest.modules.apply)."""
    return {row["id"] for row in regions if row.get("modules")}


def allen_records(loaded: dict[str, list[dict]], loader: Callable) -> list[Record]:
    """Allen connectivity claims for every loaded atlas with MBA regions (the Allen mouse atlas), as records: the
    outputs and inputs of every module's regions (ADR 0031)."""
    records = []
    for atlas, rows in loaded.items():
        if not rows or not rows[0]["id"].startswith("MBA:"):
            continue
        acronyms = {int(row["id"].split(":")[1]): row["acronym"] for row in rows}
        for claim in loader(atlas, structures(rows), acronyms):
            records.append(Record(FOLDER / f"{claim['id']}.yaml", "ConnectivityClaim", claim))
    return records


def check_generated(committed: list[Record], generated: list[Record]) -> list[Finding]:
    """The per-file rules for each generated claim, and the cross-file rules over everything."""
    findings = [finding for record in generated for finding in check_file(record)]
    return sorted(findings + check_tree(committed + generated))
