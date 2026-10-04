"""Every claim row says under which terms it may be reused (ADR 0005, ADR 0013)."""

from build.tables import rows
from build.terms import ALLEN, PROJECT, terms_of


def test_allen_claims_keep_the_allen_terms():
    assert terms_of({"extra": {"allen.experiment": 1}}) == ALLEN == "allen-institute"
    assert terms_of({"extra": None}) == terms_of({}) == PROJECT == "cc-by-4.0"


def test_claim_rows_carry_their_terms(valid_tree):
    from checks.loading import load_tree

    records, _ = load_tree(valid_tree)
    tables = rows(records)
    assert {row["terms"] for row in tables["connectivity_claims"]} == {PROJECT}
    assert {row["terms"] for row in tables["homology_claims"]} == {PROJECT}
    assert all(edge["terms"] == [PROJECT] for edge in tables["edges"])
