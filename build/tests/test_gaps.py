"""Gap mode (sprint 3.5, ADR 0027): an amygdala region nobody has injected, and the targets its neighbours reach."""

import json

from build.cli import main
from build.gaps import find_gaps
from build.tests.test_connectivity import claim as generated
from build.tests.test_connectivity import connectivity
from build.tests.test_meshes import CENTER, FakeAtlas, cube
from build.tests.test_reconcile import claim, paper, region
from build.tests.test_regions import USED, amygdala_loader, fake_loader

# The amygdala (AMY) has three nuclei: LA and BLA are injected, IA isn't. BLA has two subdivisions, BLAa (injected)
# and BLAv (not). PL, CP and BST are targets outside it; RAT is a region in another species's atlas.
REGIONS = [
    region(1, "AMY", amygdala=True), region(2, "LA", parent=1), region(3, "BLA", parent=1), region(4, "IA", parent=1),
    region(31, "BLAa", parent=3), region(32, "BLAv", parent=3),
    region(10, "PL"), region(11, "CP"), region(12, "BST"),
]
GAP = "MBA:{}|projects_to|MBA:{}|NCBITaxon:10090"


def test_an_uninjected_region_gets_its_neighbours_targets():
    gaps = find_gaps([claim(2, 10, 0.3), claim(31, 11, 0.2), claim(31, 10, 0.05)], REGIONS)
    ia = [g for g in gaps if g["subject_id"] == "MBA:4"]
    assert [g["object_id"] for g in ia] == ["MBA:10", "MBA:11"]
    assert ia[0] == {"id": GAP.format(4, 10), "subject_id": "MBA:4", "object_id": "MBA:10", "atlas": "allen-mouse-ccf-2017",
                     "species": "NCBITaxon:10090",
                     "basis": "neighbours", "density": 0.3,
                     "suggested_by": [GAP.format(2, 10), GAP.format(31, 10)]}  # LA, and BLA through its subdivision


def test_a_subdivision_is_tested_through_its_parent_or_children_and_untested_alone():
    gaps = find_gaps([claim(2, 10, 0.3), claim(31, 11, 0.2)], REGIONS)
    subjects = {g["subject_id"] for g in gaps}
    assert "MBA:3" not in subjects  # BLA: its subdivision BLAa was injected
    assert "MBA:2" not in subjects  # LA: injected
    assert "MBA:32" in subjects  # BLAv: neither it nor BLA was injected; its neighbour BLAa was
    assert [g["object_id"] for g in gaps if g["subject_id"] == "MBA:32"] == ["MBA:11"]
    # An injection into BLA itself tests BLAv too.
    assert "MBA:32" not in {g["subject_id"] for g in find_gaps([claim(3, 11, 0.2), claim(31, 10, 0.1)], REGIONS)}


def test_any_claim_about_a_regions_outputs_counts_as_tested():
    # A paper that looked at IA and found nothing still tested it.
    gaps = find_gaps([claim(2, 10, 0.3), paper(4, 12, result="absent")], REGIONS)
    assert not [g for g in gaps if g["subject_id"] == "MBA:4"]


def test_only_present_projections_suggest_and_never_into_the_region_itself():
    gaps = find_gaps([claim(2, 10, 0.3, result="absent"), claim(2, 4, 0.2), claim(2, 1, 0.1)], REGIONS)
    assert not [g for g in gaps if g["subject_id"] == "MBA:4"]  # LA → IA and LA → AMY are into IA or around it


def test_retracted_claims_and_densityless_suggestions():
    gaps = find_gaps([claim(2, 10, 0.3, status="retracted"), claim(2, 12)], REGIONS)
    assert [(g["object_id"], g["density"]) for g in gaps if g["subject_id"] == "MBA:4"] == [("MBA:12", None)]


def test_regions_outside_the_amygdala_and_unknown_regions_get_none():
    assert all(g["subject_id"] in {"MBA:4", "MBA:32"} for g in find_gaps([claim(2, 10, 0.3), claim(31, 11, 0.2)], REGIONS))
    assert find_gaps([claim(2, 999, 0.3)], REGIONS) == []


def test_the_build_puts_gaps_in_the_snapshot_and_meshes_their_regions(valid_tree, tmp_path):
    # The fake atlas's amygdala region (MBA:295) gets a parent and an uninjected sibling, MBA:5001.
    def loader(atlas, terms):
        rows = fake_loader([*USED, "MBA:5000", "MBA:5001"])(atlas, terms)
        for row in rows:
            if row["id"] in ("MBA:295", "MBA:5001"):
                row["parent"] = "MBA:5000"
            if row["id"] == "MBA:5001":
                row["amygdala"] = True
        return rows

    meshes = FakeAtlas({"root": cube(CENTER, 8000), 5001: cube(CENTER), **{int(i.split(":")[1]): cube(CENTER) for i in USED}})
    snapshot, brain = tmp_path / "snapshot.json", tmp_path / "brain"
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--snapshot", str(snapshot), "--meshes", str(brain)],
                atlas_loader=loader, amygdala_loader=amygdala_loader, connectivity_loader=connectivity(generated()),
                mesh_opener=lambda name, version: meshes) == 0
    rows = json.loads(snapshot.read_text(encoding="utf-8"))["tables"]["gaps"]
    assert {"MBA:5001|projects_to|MBA:536|NCBITaxon:10090"} <= {row["id"] for row in rows}
    assert all(row["subject_id"] == "MBA:5001" for row in rows)
    assert "MBA:5001" in json.loads((brain / "allen-mouse-ccf-2017" / "index.json").read_text(encoding="utf-8"))["regions"]
    assert (tmp_path / "dist" / "gaps.csv").read_text(encoding="utf-8").count("\n") == 1  # the header only: never dumped
