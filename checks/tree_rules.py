"""Rules that look across data files: IDs, references, atlas species and cited sources."""

from collections import defaultdict

from checks.findings import Finding, Record
from checks.identifiers import citation_of, is_open_licence, source_key

CLAIMS = ("ConnectivityClaim", "HomologyClaim")


def _refs(record: Record) -> list[tuple[dict, str | None]]:
    """Each entity reference in a record, with the species that side of it is in (None if not stated)."""
    data = record.data
    pick = lambda key: data.get(key) if isinstance(data.get(key), dict) else None
    if record.cls == "ConnectivityClaim":
        pairs = [(pick("subject"), data.get("species")), (pick("object"), data.get("species"))]
    elif record.cls == "HomologyClaim":
        pairs = [(pick("subject"), data.get("subject_species")), (pick("object"), data.get("object_species"))]
    elif record.cls == "NeuronType":
        pairs = [(pick("region"), None)]
    else:
        pairs = []
    return [(ref, species) for ref, species in pairs if ref is not None]


def check_tree(records: list[Record]) -> list[Finding]:
    findings = []

    by_id = defaultdict(list)
    for record in records:
        if isinstance(record.data.get("id"), str):
            by_id[record.data["id"]].append(record)
    for record_id, holders in by_id.items():
        if len(holders) > 1:
            others = ", ".join(str(r.path) for r in holders)
            findings += [Finding(str(r.path), "duplicate-id", f"ID {record_id} is also used by: {others}") for r in holders]

    ids_of = lambda cls: [r for r in records if r.cls == cls and isinstance(r.data.get("id"), str)]
    neuron_types = {r.data["id"] for r in ids_of("NeuronType")}
    atlas_species = {r.data["id"]: r.data.get("species") for r in ids_of("Atlas")}

    for record in records:
        atlases = [r.get("atlas") for r, _ in _refs(record)]
        if record.cls == "Region":
            atlases.append(record.data.get("atlas"))
        for atlas in atlases:
            if isinstance(atlas, str) and atlas not in atlas_species:
                findings.append(Finding(str(record.path), "unknown-reference", f"atlas {atlas} has no record in entities/atlases/"))
        for ref, species in _refs(record):
            ref_id = ref.get("id")
            if isinstance(ref_id, str) and ref_id.startswith("nt-") and ref_id not in neuron_types:
                findings.append(Finding(str(record.path), "unknown-reference", f"neuron type {ref_id} has no record in entities/neuron_types/"))
            atlas = ref.get("atlas") if isinstance(ref.get("atlas"), str) else None
            if record.cls in CLAIMS and isinstance(species, str) and atlas in atlas_species and atlas_species[atlas] != species:
                findings.append(Finding(str(record.path), "atlas-species",
                                        f"{ref_id} is in {atlas} ({atlas_species[atlas]}), but this side of the claim is {species}"))
    return findings + _source_rules(records) + _allowlist_rules(records)


def _accepts(entries: list[dict], source: dict) -> bool:
    """Whether an allowlist entry accepts a source record: its kind, and its journal where the entry names venues."""
    return any(entry.get("kind") == source.get("kind")
               and ("venues" not in entry or source.get("journal") in entry["venues"]) for entry in entries)


def _allowlist_rules(records: list[Record]) -> list[Finding]:
    """Every claim cites a kind of source the allowlist accepts (ADR 0015). Without an allowlist, none is accepted."""
    entries = [entry for r in records if r.cls == "Allowlist" and isinstance(r.data.get("accepted"), list)
               for entry in r.data["accepted"] if isinstance(entry, dict)]
    sources = {r.data["id"].lower(): r.data for r in records if r.cls == "Source" and isinstance(r.data.get("id"), str)}
    findings = []
    for record in records:
        key = source_key(citation_of(record.data)) if record.cls in CLAIMS else None
        source = sources.get(key.lower()) if key else None
        if source is None or _accepts(entries, source):
            continue  # A missing source record is the missing-source rule's finding.
        venue = f" from {source['journal']}" if isinstance(source.get("journal"), str) else ""
        findings.append(Finding(str(record.path), "source-not-allowed",
                                f"cites {key}, a {source.get('kind', 'source of unknown kind')}{venue}, "
                                "which allowlist.yaml doesn't accept"))
    return findings


def _source_rules(records: list[Record]) -> list[Finding]:
    """Every citation has a source record; claims on retracted papers are retracted; excerpts need an open licence."""
    findings = []
    sources = {r.data["id"].lower(): r.data for r in records if r.cls == "Source" and isinstance(r.data.get("id"), str)}
    for record in records:
        if record.cls not in CLAIMS:
            continue
        key = source_key(citation_of(record.data))
        source = sources.get(key.lower()) if key else None
        if key and source is None:
            findings.append(Finding(str(record.path), "missing-source",
                                    f"cites {key}, which has no record in sources/; run python -m checks sources"))
        if source is not None and source.get("retracted") is True and record.data.get("status") != "retracted":
            findings.append(Finding(str(record.path), "cites-retracted",
                                    f"cites {key}, which is retracted; set status: retracted and log it in retractions.yaml"))
        if "excerpt" in record.data:
            licence = source.get("license") if source is not None else None
            if not is_open_licence(licence):
                findings.append(Finding(str(record.path), "excerpt-licence",
                                        f"has an excerpt, but its source's licence ({licence or 'none'}) isn't CC BY or CC0; use a paraphrase"))
    return findings
