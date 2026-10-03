"""Atlas regions in the build: loaded per atlas record, checked against the data, merged into the database rows."""

import re

from checks.findings import Finding, Record

REGION_ID = re.compile(r"^(MBA|HBA|DHBA):\d+$")


def _region_refs(record: Record) -> list[dict]:
    data = record.data
    if record.cls in ("ConnectivityClaim", "HomologyClaim"):
        return [data["subject"], data["object"]]
    if record.cls == "NeuronType":
        return [data["region"]]
    if record.cls == "Region":
        return [{"id": data["id"], "atlas": data["atlas"]}]
    return []


def unknown_regions(records: list[Record], regions: dict[str, list[dict]]) -> list[Finding]:
    """References to atlas regions that the loaded atlas doesn't have (an atlas loaded without regions has none)."""
    known = {atlas: {row["id"] for row in rows} for atlas, rows in regions.items()}
    findings = []
    for record in records:
        for ref in _region_refs(record):
            atlas, region = ref.get("atlas"), ref.get("id")
            if atlas in known and REGION_ID.match(str(region)) and region not in known[atlas]:
                findings.append(Finding(str(record.path), "unknown-region", f"{region} is not a region of {atlas}"))
    return sorted(findings)


def amygdala(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["amygdala"]]


def summary(atlas: str, rows: list[dict]) -> str:
    found = amygdala(rows)
    return f"{atlas}: {len(rows)} regions; amygdala: " + (", ".join(f"{r['acronym']} ({r['id']})" for r in found) or "none")


def merge(tables: dict[str, list[dict]], regions: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """The tables with the atlas regions added to `regions` (for the database only; dumps keep the files' regions)."""
    from_files = {row["id"] for row in tables["regions"]}
    added = [row for rows in regions.values() for row in rows if row["id"] not in from_files]
    return {**tables, "regions": sorted(tables["regions"] + added, key=lambda row: row["id"])}
