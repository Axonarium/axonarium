"""Edges: connectivity claims aggregated per subject, predicate, object and species. Never edited by hand."""

from checks.findings import Record

STRENGTHS = ("weak", "moderate", "strong")  # Ordinal, weakest first


def compute_edges(records: list[Record]) -> list[dict]:
    """One edge per subject, predicate, object and species, from the connectivity claims that aren't retracted."""
    groups: dict[str, list[dict]] = {}
    for record in records:
        claim = record.data
        if record.cls != "ConnectivityClaim" or claim.get("status") == "retracted":
            continue
        key = "|".join((claim["subject"]["id"], claim["predicate"], claim["object"]["id"], claim["species"]))
        groups.setdefault(key, []).append(claim)
    edges = []
    for key, claims in sorted(groups.items()):
        first = claims[0]
        results = [c["result"] for c in claims]
        present = [c.get("strength") for c in claims if c["result"] == "present" and c.get("strength") in STRENGTHS]
        densities = [m["value"] for c in claims if c["result"] == "present" for m in c.get("measurements") or []
                     if m["quantity"] == "projection_density"]
        edges.append({
            "id": key,
            "subject_id": first["subject"]["id"],
            "subject_type": first["subject"]["type"],
            "predicate": first["predicate"],
            "object_id": first["object"]["id"],
            "object_type": first["object"]["type"],
            "species": first["species"],
            "n_claims": len(claims),
            "n_present": results.count("present"),
            "n_absent": results.count("absent"),
            "n_ambiguous": results.count("ambiguous"),
            "n_disputed": sum(c.get("status") == "disputed" for c in claims),
            "evidence_classes": sorted({c["evidence_class"] for c in claims}),
            "strength": max(present, key=STRENGTHS.index) if present else None,
            "density": max(densities) if densities else None,  # the strongest projection density found
            "signs": sorted({c["sign"] for c in claims}),
            "claim_ids": sorted(c["id"] for c in claims),
        })
    return edges
