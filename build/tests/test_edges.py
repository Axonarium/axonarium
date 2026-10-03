"""Edges are computed from connectivity claims, never edited by hand."""

from pathlib import Path

from build.edges import compute_edges
from checks.loading import load_tree


def claim(claim_id, result="present", evidence="anterograde_tracer", status="accepted", strength=None, sign="unknown",
          subject="MBA:295", obj="MBA:559", species="NCBITaxon:10090"):
    data = {"id": claim_id, "subject": {"type": "region", "id": subject}, "predicate": "projects_to",
            "object": {"type": "region", "id": obj}, "species": species, "evidence_class": evidence,
            "result": result, "sign": sign, "status": status}
    if strength:
        data["strength"] = strength
    from checks.findings import Record
    return Record(Path(f"{claim_id}.yaml"), "ConnectivityClaim", data)


def test_edges_aggregate_claims():
    edges = compute_edges([claim("clm-a", evidence="retrograde_tracer"), claim("clm-b"), claim("clm-c", result="absent")])
    assert edges == [{
        "id": "MBA:295|projects_to|MBA:559|NCBITaxon:10090",
        "subject_id": "MBA:295", "subject_type": "region", "predicate": "projects_to",
        "object_id": "MBA:559", "object_type": "region", "species": "NCBITaxon:10090",
        "n_claims": 3, "n_present": 2, "n_absent": 1, "n_ambiguous": 0, "n_disputed": 0,
        "evidence_classes": ["anterograde_tracer", "retrograde_tracer"], "strength": None,
        "signs": ["unknown"], "claim_ids": ["clm-a", "clm-b", "clm-c"],
    }]


def test_retracted_claims_excluded():
    edges = compute_edges([claim("clm-a", status="retracted"), claim("clm-b", obj="MBA:536")])
    assert [e["object_id"] for e in edges] == ["MBA:536"]


def test_strongest_strength_among_present():
    edges = compute_edges([claim("clm-a", strength="weak"), claim("clm-b", strength="strong", result="absent"),
                           claim("clm-c", strength="moderate")])
    assert edges[0]["strength"] == "moderate"


def test_disputed_counted():
    edges = compute_edges([claim("clm-a", status="disputed"), claim("clm-b")])
    assert (edges[0]["n_claims"], edges[0]["n_disputed"]) == (2, 1)


def test_valid_tree_edges(valid_tree):
    records, _ = load_tree(valid_tree)
    claims = [r for r in records if r.cls == "ConnectivityClaim" and r.data["status"] != "retracted"]
    keys = {(c.data["subject"]["id"], c.data["predicate"], c.data["object"]["id"], c.data["species"]) for c in claims}
    edges = compute_edges(records)
    assert len(edges) == len(keys) and sum(e["n_claims"] for e in edges) == len(claims)
    assert [e["id"] for e in edges] == sorted(e["id"] for e in edges)
