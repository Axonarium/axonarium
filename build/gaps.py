"""Gap mode (sprint 3.5, ADR 0027): connections that are plausible but untested, as research prompts.

An amygdala region's outputs are untested in a species when no claim names an output of it in that species: not of
the region, nor of a subdivision of it, nor of a region it is part of. No experiment is known to have injected it.
A connection from such a region to a target is plausible when a neighbour, another subdivision of the same parent,
projects there: a present claim from the neighbour or one of its subdivisions. The gap keeps the connections that
suggest it, and the strongest projection density among them.

Inputs are left out. Allen's claims for injections outside the amygdala keep only densities of at least 0.01, so
there a missing claim can't tell an untested region from a weak connection. Gaps are suggestions, never evidence:
they are not claims, and they are never dumped, because they rest on Allen claims and atlas regions (ADR 0005).
"""

from collections import defaultdict

from build.connectivity import amygdala_regions

BASIS = "neighbours"  # how a gap was suggested; homology across species may join later (ADR 0027)


def _density(claim: dict) -> float | None:
    values = [m["value"] for m in claim.get("measurements") or [] if m.get("quantity") == "projection_density"]
    return max(values) if values else None


def find_gaps(claims: list[dict], regions: list[dict]) -> list[dict]:
    """Gap rows for these connectivity claims (committed and build-time) over the atlases' `regions`, sorted by ID."""
    parent = {row["id"]: row["parent"] for row in regions}
    atlas = {row["id"]: row["atlas"] for row in regions}
    children: dict[str, list[str]] = defaultdict(list)
    for row in regions:
        if row["parent"]:
            children[row["parent"]].append(row["id"])

    def ancestors(region: str) -> set[str]:
        found = set()
        while (region := parent.get(region)) and region not in found:
            found.add(region)
        return found

    def subtree(region: str) -> set[str]:
        found, stack = set(), [region]
        while stack:
            if (current := stack.pop()) not in found:
                found.add(current)
                stack.extend(children.get(current, []))
        return found

    amygdala = amygdala_regions(regions)
    live = [c for c in claims if c.get("status") != "retracted" and c["subject"].get("type") == "region"
            and c["object"].get("type") == "region" and c["subject"]["id"] in parent and c["object"]["id"] in parent]
    by_species: dict[str, list[dict]] = defaultdict(list)
    for claim in live:
        by_species[claim["species"]].append(claim)

    gaps: dict[str, dict] = {}
    for species, found in by_species.items():
        # A region is tested when a claim names an output of it, of a subdivision, or of a region it is part of.
        tested: set[str] = set()
        for subject in {c["subject"]["id"] for c in found}:
            tested |= {subject} | ancestors(subject) | subtree(subject)
        outputs: dict[str, list[dict]] = defaultdict(list)
        for claim in found:
            if claim["result"] == "present" and claim["predicate"] == "projects_to":
                outputs[claim["subject"]["id"]].append(claim)
        for region in sorted(amygdala - tested):
            mother = parent.get(region)
            if not mother:
                continue
            itself = {region} | ancestors(region) | subtree(region)
            for neighbour in children[mother]:
                if neighbour == region:
                    continue
                for subject in subtree(neighbour):
                    for claim in outputs.get(subject, []):
                        target = claim["object"]["id"]
                        if target in itself:
                            continue
                        key = "|".join((region, "projects_to", target, species))
                        gap = gaps.setdefault(key, {"id": key, "subject_id": region, "object_id": target,
                                                    "atlas": atlas[region], "species": species, "basis": BASIS,
                                                    "density": None, "suggested_by": set()})
                        gap["suggested_by"].add("|".join((subject, "projects_to", target, species)))
                        density = _density(claim)
                        if density is not None and (gap["density"] is None or density > gap["density"]):
                            gap["density"] = density
    return [{**gap, "suggested_by": sorted(gap["suggested_by"])} for _, gap in sorted(gaps.items())]
