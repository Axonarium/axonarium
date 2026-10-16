"""The rat in 3D (ADR 0034): the bridge from UBERON to the Waxholm rat atlas, and the meshes the build draws with it."""

import json
import re
import shutil
from pathlib import Path

import yaml

from build import waxholm
from build.cli import main
from build.tests.test_meshes import CENTER, FakeAtlas, cube
from build.tests.test_regions import TERMS, fake_loader, no_claims
from checks.findings import Record

WAXHOLM = Path(__file__).resolve().parents[2] / "data" / "entities" / "atlases" / f"{waxholm.ATLAS}.yaml"

AMYGDALA, BASAL, CENTRAL, LATERAL = "UBERON:0001876", "UBERON:0002887", "UBERON:0002883", "UBERON:0002886"
HIPPOCAMPAL, CA1 = "UBERON:0002421", "UBERON:0003881"
BRIDGE = [{"structure": 501, "term": AMYGDALA, "label": "amygdala"},
          {"structure": 1021, "term": HIPPOCAMPAL, "label": "hippocampal formation"},
          {"structure": 98, "term": CA1, "label": "CA1 field of hippocampus"}]
UNDER = {AMYGDALA: {AMYGDALA: "amygdala", BASAL: "basal amygdaloid nucleus", CENTRAL: "central amygdaloid nucleus",
                    LATERAL: "lateral amygdaloid nucleus"},
         HIPPOCAMPAL: {HIPPOCAMPAL: "hippocampal formation", CA1: "CA1 field of hippocampus"},
         CA1: {CA1: "CA1 field of hippocampus"}}


def rat_claim(subject, object_, species=waxholm.RAT):
    return Record(path=None, cls="ConnectivityClaim", data={
        "species": species, "subject": {"type": "region", "id": subject}, "object": {"type": "region", "id": object_}})


def test_rat_terms_counts_the_rat_claims_terms():
    named = waxholm.rat_terms([rat_claim(BASAL, CENTRAL), rat_claim(BASAL, CA1),
                               rat_claim("MBA:295", "MBA:536", species="NCBITaxon:10090")])
    assert named == {BASAL: 2, CENTRAL: 1, CA1: 1}


def test_a_term_is_drawn_on_the_most_specific_row_that_covers_it():
    placed = waxholm.resolve([BASAL, CA1, HIPPOCAMPAL, "UBERON:0001898"], BRIDGE, UNDER)
    assert placed[BASAL]["structure"] == 501  # a nucleus Waxholm lacks takes the amygdaloid area
    assert placed[CA1]["structure"] == 98  # its own row, not the hippocampal formation's
    assert placed[HIPPOCAMPAL]["structure"] == 1021
    assert "UBERON:0001898" not in placed  # no row covers it: the network view only


def test_bridge_problems():
    structures = {501: {}, 1021: {}}
    bridge = BRIDGE + [{"structure": 501, "term": AMYGDALA, "label": "amygdala"},
                       {"structure": 1021, "term": "UBERON:9999999", "label": "nothing"}]
    assert waxholm.problems(bridge, structures, UNDER) == [
        "build/waxholm.yaml: Waxholm has no structure 98 (for CA1 field of hippocampus)",
        "build/waxholm.yaml: OLS doesn't know UBERON:9999999 (nothing)",
        "build/waxholm.yaml: UBERON:0001876 is listed 2 times"]
    assert waxholm.problems(BRIDGE, {501: {}, 1021: {}, 98: {}}, UNDER) == []


def test_relabelled_terms_are_noted():
    renamed = {**UNDER, CA1: {CA1: "field CA1"}}
    assert waxholm.relabelled(BRIDGE, renamed) == [
        "build/waxholm.yaml: UBERON now labels UBERON:0003881 'field CA1', not 'CA1 field of hippocampus'"]


def test_the_bridge_file():
    bridge = waxholm.read_bridge()
    assert bridge and all(set(row) == {"structure", "term", "label"} for row in bridge)
    assert all(isinstance(row["structure"], int) and re.fullmatch(r"UBERON:\d{7}", row["term"]) for row in bridge)
    assert len({row["term"] for row in bridge}) == len(bridge)


class FakeWaxholm(FakeAtlas):
    def __init__(self, meshes):
        super().__init__(meshes, version="3.0")
        self.metadata["name"] = "whs_sd_rat"


def test_build_draws_rat_claims_on_waxholm(valid_tree, tmp_path, capsys, monkeypatch):
    shutil.copy(WAXHOLM, valid_tree / "entities" / "atlases")
    monkeypatch.setattr(waxholm, "read_bridge", lambda: BRIDGE)
    mouse = FakeAtlas({"root": cube(CENTER, 8000), **{n: cube(CENTER) for n in range(1, 2000)}})
    rat = FakeWaxholm({"root": cube(CENTER, 8000), 501: cube(CENTER + [0, 0, 2000]), 1021: None, 98: None})

    def terms_loader(roots):
        return TERMS if roots == list(TERMS) else {root: UNDER[root] for root in roots}

    brain = tmp_path / "brain"
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--meshes", str(brain)],
                atlas_loader=fake_loader(empty={waxholm.ATLAS}), terms_loader=terms_loader, connectivity_loader=no_claims,
                mesh_opener=lambda name, version: rat if name == "whs_sd_rat_39um" else mouse) == 0
    index = json.loads((brain / waxholm.ATLAS / "index.json").read_text(encoding="utf-8"))
    # The valid tree's one rat claim: the lateral amygdaloid nucleus to the central, both on the amygdaloid area.
    assert sorted(index["regions"]) == [CENTRAL, LATERAL]
    assert {region["file"] for region in index["regions"].values()} == {"501.glb"}
    assert index["regions"][LATERAL]["name"] == "lateral amygdaloid nucleus"
    assert "meshes: 2 of 2 rat region(s) drawn on waxholm-sd-rat-v4" in capsys.readouterr().out


def test_a_broken_bridge_stops_the_build(valid_tree, tmp_path, capsys, monkeypatch):
    shutil.copy(WAXHOLM, valid_tree / "entities" / "atlases")
    monkeypatch.setattr(waxholm, "read_bridge", lambda: BRIDGE)
    mouse = FakeAtlas({"root": cube(CENTER, 8000), **{n: cube(CENTER) for n in range(1, 2000)}})
    rat = FakeWaxholm({"root": cube(CENTER, 8000), 501: cube(CENTER)})  # no 1021 or 98

    def terms_loader(roots):
        return TERMS if roots == list(TERMS) else {root: UNDER[root] for root in roots}

    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--meshes", str(tmp_path / "brain")],
                atlas_loader=fake_loader(empty={waxholm.ATLAS}), terms_loader=terms_loader, connectivity_loader=no_claims,
                mesh_opener=lambda name, version: rat if name == "whs_sd_rat_39um" else mouse) == 1
    out = capsys.readouterr().out
    assert "Waxholm has no structure 1021" in out and "problem(s) in the Waxholm bridge" in out


def test_the_pinned_atlas_is_the_rat_atlas():
    record = yaml.safe_load(WAXHOLM.read_text(encoding="utf-8"))
    assert record["id"] == waxholm.ATLAS and record["species"] == waxholm.RAT
