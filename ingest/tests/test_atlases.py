"""Atlas regions from BrainGlobe and UBERON bridges, on synthetic fixtures (no network, no atlas content)."""

from pathlib import Path

import pytest

from ingest.atlases import AtlasPinMismatch, bridge_mappings, load_atlas, region_rows

BRIDGE = (Path(__file__).parent / "fixtures" / "bridge.owl").read_text(encoding="utf-8")
STRUCTURES = [
    {"id": 997, "name": "root", "acronym": "root", "parent_structure_id": None},
    {"id": 1, "name": "Region one", "acronym": "R1", "parent_structure_id": 997},
    {"id": 2, "name": "Region two, layer 2", "acronym": "R2-2", "parent_structure_id": 1},
]
MOUSE = {"id": "allen-mouse-ccf-2017", "brainglobe_name": "allen_mouse_25um", "extra": {"brainglobe.atlas_version": "3.1"}}


class FakeAtlas:
    def __init__(self, name: str, version: str):
        self.metadata = {"name": name, "version": version}
        self.structures = {s["acronym"]: s for s in STRUCTURES}


def test_bridge_exact_mapping():
    assert bridge_mappings(BRIDGE, "MBA") == {"MBA:1": "UBERON:0000001"}


def test_nested_intersection_not_exact():
    assert "MBA:2" not in bridge_mappings(BRIDGE, "MBA")


def test_region_rows():
    rows = region_rows("allen-mouse-ccf-2017", STRUCTURES, "MBA", {"MBA:1": "UBERON:0000001"})
    assert rows[0] == {"id": "MBA:1", "name": "Region one", "acronym": "R1", "atlas": "allen-mouse-ccf-2017",
                       "parent": "MBA:997", "uberon": "UBERON:0000001", "synonyms": None, "extra": None}
    assert [r["id"] for r in rows] == ["MBA:1", "MBA:2", "MBA:997"] and rows[2]["parent"] is None


def test_load_atlas_reads_brainglobe_and_bridge():
    rows = load_atlas(MOUSE, open_atlas=lambda name: FakeAtlas("allen_mouse", "3.1"), fetch=lambda url: BRIDGE)
    assert {r["id"]: r["uberon"] for r in rows}["MBA:1"] == "UBERON:0000001"


def test_pin_mismatch_stops():
    with pytest.raises(AtlasPinMismatch, match="3.1.*3.2"):
        load_atlas(MOUSE, open_atlas=lambda name: FakeAtlas("allen_mouse", "3.2"), fetch=lambda url: BRIDGE)


def test_unpinned_atlas_stops():
    with pytest.raises(AtlasPinMismatch, match="brainglobe.atlas_version"):
        load_atlas({**MOUSE, "extra": None}, open_atlas=lambda name: FakeAtlas("allen_mouse", "3.1"), fetch=lambda url: BRIDGE)


def test_atlas_without_region_ids_gives_no_regions():
    rat = {"id": "waxholm-sd-rat-v4", "brainglobe_name": "whs_sd_rat_39um", "extra": {"brainglobe.atlas_version": "3.0"}}
    assert load_atlas(rat, open_atlas=lambda name: FakeAtlas("whs_sd_rat", "3.0"), fetch=lambda url: BRIDGE) == []
