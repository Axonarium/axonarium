"""Allen connectivity claims from synthetic API answers (no network, no Allen data)."""

from pathlib import Path

from checks.file_rules import check_file
from checks.findings import Record
from ingest.allen_connectivity import build_claims, claim_id, experiments, load_claims

ATLAS = "allen-mouse-ccf-2017"
ACRONYMS = {295: "BLA", 536: "CEA", 131: "LA", 997: "root"}


def experiment(eid, structure, lines=()):
    return {"id": eid, "specimen": {"donor": {"transgenic_lines": [{"name": n} for n in lines]},
                                    "stereotaxic_injections": [{"primary_injection_structure": {"id": structure, "acronym": ACRONYMS[structure]}}]}}


def fake_get(answers):
    asked = []

    def get(criteria, num_rows=2000):
        asked.append(criteria)
        for key, value in answers.items():
            if key in criteria:
                return value
        raise AssertionError(f"unexpected query {criteria}")
    get.asked = asked
    return get


ANSWERS = {
    "model::SectionDataSet": [experiment(1, 295), experiment(2, 295, ["Slc32a1-IRES-Cre"])],
    "structure_sets": [{"id": 536}, {"id": 131}, {"id": 295}],
    "section_data_set_id$eq1],[is_injection$eqtrue]": [{"structure_id": 295, "projection_volume": 0.06},
                                                       {"structure_id": 131, "projection_volume": 0.04}],
    "section_data_set_id$eq1],[is_injection$eqfalse]": [{"structure_id": 536, "projection_density": 0.2},
                                 {"structure_id": 131, "projection_density": 0.004},
                                 {"structure_id": 295, "projection_density": 0.9},
                                 {"structure_id": 997, "projection_density": 0.5}],
}


def test_wild_type_only():
    found = experiments(fake_get(ANSWERS), [295])
    assert [e["id"] for e in found] == [1]


def test_targets():
    claims = load_claims(ATLAS, [295], ACRONYMS, get=fake_get(ANSWERS))
    # CEA only: LA is below 0.01, BLA is the injection structure, root isn't a summary structure.
    assert [(c["subject"]["id"], c["object"]["id"]) for c in claims] == [("MBA:295", "MBA:536")]
    claim = claims[0]
    assert claim["measurements"] == [{"quantity": "projection_density", "value": 0.2, "unit": "1"}]
    assert claim["source"] == {"doi": "10.1038/nature13186", "locator": "Allen Mouse Brain Connectivity Atlas, experiment 1"}
    assert claim["curation"]["role"] == "ingester" and claim["status"] == "accepted"
    assert claim["extra"] == {"allen.experiment": 1, "allen.injection_share": 0.6} and "60% of the injection in BLA" in claim["paraphrase"]


def test_claims_pass_the_checks():
    for claim in load_claims(ATLAS, [295], ACRONYMS, get=fake_get(ANSWERS)):
        assert check_file(Record(Path(f"{claim['id']}.yaml"), "ConnectivityClaim", claim)) == []


def test_rerun_is_identical():
    assert load_claims(ATLAS, [295], ACRONYMS, get=fake_get(ANSWERS)) == load_claims(ATLAS, [295], ACRONYMS, get=fake_get(ANSWERS))


def test_claim_ids_are_stable_and_valid():
    assert claim_id(1, 536) == claim_id(1, 536) != claim_id(1, 131)
    assert len(claim_id(1, 536)) == 14 and claim_id(1, 536).startswith("clm-")
    assert set(claim_id(1, 536)[4:]) <= set("0123456789abcdefghjkmnpqrstvwxyz")


def test_no_amygdala_structures_no_queries():
    get = fake_get(ANSWERS)
    assert load_claims(ATLAS, [], ACRONYMS, get=get) == [] and get.asked == []


def test_build_claims_is_pure():
    claims = build_claims(ATLAS, [{"id": 1, "injection": 295, "share": 0.6, "injected": {295}}], {536},
                          {1: [{"structure_id": 536, "projection_density": 0.0123456789}]}, ACRONYMS)
    assert claims[0]["measurements"][0]["value"] == 0.012346 and "BLA" in claims[0]["paraphrase"] and "CEA" in claims[0]["paraphrase"]


def test_targets_outside_the_pinned_atlas_skipped():
    # Allen's summary-structure list has a few structures the pinned atlas (2017 annotation) lacks.
    claims = build_claims(ATLAS, [{"id": 1, "injection": 295, "share": 0.6, "injected": {295}}], {536, 460}, {1: [{"structure_id": 460, "projection_density": 0.3},
                                                                                    {"structure_id": 536, "projection_density": 0.2}]}, ACRONYMS)
    assert [c["object"]["id"] for c in claims] == ["MBA:536"]


def test_targets_that_received_tracer_skipped():
    # Spill-over: tracer injected into a neighbour labels it at the injection site, not by projection.
    claims = build_claims(ATLAS, [{"id": 1, "injection": 295, "share": 0.6, "injected": {295, 536}}], {536, 131},
                          {1: [{"structure_id": 536, "projection_density": 0.3}, {"structure_id": 131, "projection_density": 0.2}]}, ACRONYMS)
    assert [c["object"]["id"] for c in claims] == ["MBA:131"]


def test_mostly_off_target_injections_are_proposed():
    claims = build_claims(ATLAS, [{"id": 1, "injection": 295, "share": 0.3, "injected": {295}}], {536},
                          {1: [{"structure_id": 536, "projection_density": 0.3}]}, ACRONYMS)
    assert claims[0]["status"] == "proposed" and "30% of the injection in BLA" in claims[0]["paraphrase"]
