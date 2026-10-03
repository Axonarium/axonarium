"""Rules that look across data files: IDs, references and atlas species."""

from collections import defaultdict

from checks.findings import Finding, Record

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
    return findings
