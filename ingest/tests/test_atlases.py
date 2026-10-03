"""Atlas regions from BrainGlobe and UBERON bridges, on synthetic fixtures (no network, no atlas content)."""

import hashlib
from pathlib import Path

import pytest

from ingest.atlases import AtlasPinMismatch, BridgeMismatch, amygdala_terms, bridge_mappings, load_atlas, region_rows

BRIDGE = (Path(__file__).parent / "fixtures" / "bridge.owl").read_text(encoding="utf-8")
BRIDGES = {"MBA": ("https://example.org/bridge.owl", hashlib.sha256(BRIDGE.encode()).hexdigest())}
# BrainGlobe 3.0.2 reads parent IDs as 16-bit integers, so parents above 65535 wrap; the ID path is right.
STRUCTURES = [
    {"id": 997, "name": "root", "acronym": "root", "parent_structure_id": None, "structure_id_path": [997]},
    {"id": 1, "name": "Region one", "acronym": "R1", "parent_structure_id": 997, "structure_id_path": [997, 1]},
    {"id": 100000, "name": "Region big", "acronym": "RB", "parent_structure_id": 1, "structure_id_path": [997, 1, 100000]},
    {"id": 2, "name": "Region two", "acronym": "R2", "parent_structure_id": 34464, "structure_id_path": [997, 1, 100000, 2]},
]
AMYGDALA = {"UBERON:0000001": "amygdala-ish nucleus"}
MOUSE = {"id": "allen-mouse-ccf-2017", "brainglobe_name": "allen_mouse_25um", "extra": {"brainglobe.atlas_version": "3.1"}}


class FakeAtlas:
    def __init__(self, name: str, version: str, structures=STRUCTURES):
        self.metadata = {"name": name, "version": version}
        self.structures = {s["acronym"]: s for s in structures}


def opener(name="allen_mouse", served="3.1", structures=STRUCTURES, asked=None):
    def open_atlas(brainglobe_name, version):
        if asked is not None:
            asked.append((brainglobe_name, version))
        return FakeAtlas(name, served, structures)
    return open_atlas


def test_bridge_exact_mapping():
    assert bridge_mappings(BRIDGE, "MBA") == {"MBA:1": "UBERON:0000001"}


def test_nested_intersection_not_exact():
    assert "MBA:2" not in bridge_mappings(BRIDGE, "MBA")


def test_part_of_restriction_not_exact():
    assert "MBA:4" not in bridge_mappings(BRIDGE, "MBA")


def test_region_rows():
    rows = region_rows("allen-mouse-ccf-2017", STRUCTURES, "MBA", {"MBA:1": "UBERON:0000001"}, AMYGDALA)
    by_id = {r["id"]: r for r in rows}
    assert by_id["MBA:1"] == {"id": "MBA:1", "name": "Region one", "acronym": "R1", "atlas": "allen-mouse-ccf-2017",
                              "parent": "MBA:997", "uberon": "UBERON:0000001", "amygdala": True,
                              "uberon_label": "amygdala-ish nucleus", "synonyms": None, "extra": None}
    assert by_id["MBA:997"]["parent"] is None and by_id["MBA:997"]["amygdala"] is False


def test_parent_from_the_id_path():
    rows = {r["id"]: r for r in region_rows("a", STRUCTURES, "MBA", {}, {})}
    assert rows["MBA:2"]["parent"] == "MBA:100000"  # not MBA:34464, the wrapped 16-bit value


def test_parent_must_be_in_the_atlas():
    orphan = [*STRUCTURES[:1], {"id": 3, "name": "Orphan", "acronym": "O", "parent_structure_id": 5, "structure_id_path": [997, 5, 3]}]
    with pytest.raises(ValueError, match="MBA:5"):
        region_rows("a", orphan, "MBA", {}, {})


def test_load_atlas_asks_for_the_pinned_version():
    asked = []
    rows = load_atlas(MOUSE, AMYGDALA, open_atlas=opener(asked=asked), fetch=lambda url: BRIDGE, bridges=BRIDGES)
    assert asked == [("allen_mouse_25um", "3.1")]
    assert {r["id"]: r["uberon"] for r in rows}["MBA:1"] == "UBERON:0000001"


def test_pin_mismatch_stops():
    with pytest.raises(AtlasPinMismatch, match="3.1.*3.2"):
        load_atlas(MOUSE, AMYGDALA, open_atlas=opener(served="3.2"), fetch=lambda url: BRIDGE, bridges=BRIDGES)


def test_unpinned_atlas_stops():
    with pytest.raises(AtlasPinMismatch, match="brainglobe.atlas_version"):
        load_atlas({**MOUSE, "extra": None}, AMYGDALA, open_atlas=opener(), fetch=lambda url: BRIDGE, bridges=BRIDGES)


def test_bridge_checksum_mismatch_stops():
    with pytest.raises(BridgeMismatch, match="sha256"):
        load_atlas(MOUSE, AMYGDALA, open_atlas=opener(), fetch=lambda url: BRIDGE + " ", bridges=BRIDGES)


def test_atlas_without_region_ids_gives_no_regions():
    rat = {"id": "waxholm-sd-rat-v4", "brainglobe_name": "whs_sd_rat_39um", "extra": {"brainglobe.atlas_version": "3.0"}}
    assert load_atlas(rat, AMYGDALA, open_atlas=opener(name="whs_sd_rat", served="3.0"), fetch=lambda url: BRIDGE) == []


def test_amygdala_terms_from_ols():
    answer = {"_embedded": {"terms": [{"obo_id": "UBERON:0002887", "label": "basal amygdaloid nucleus"},
                                      {"obo_id": "BFO:0000040", "label": "not uberon"}]},
              "page": {"totalPages": 1}}
    terms = amygdala_terms(fetch_json=lambda url: answer)
    assert terms == {"UBERON:0001876": "amygdala", "UBERON:0002887": "basal amygdaloid nucleus"}
