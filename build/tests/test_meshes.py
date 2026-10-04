"""Region meshes for the site's 3D view: BrainGlobe meshes converted to glTF at build time (ADR 0011)."""

import json
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh

from build.cli import main
from build.meshes import convert, export_atlas, regions_to_draw, right_centroid, to_viewer
from build.tests.test_regions import USED, amygdala_loader, fake_loader, no_claims
from checks.findings import Record

SHAPE_UM = (13200.0, 8000.0, 11400.0)  # allen_mouse_25um, axes: anterior->posterior, superior->inferior, right->left
CENTER = np.array(SHAPE_UM) / 2


def cube(center_asr, size=1000.0):
    """A cube in atlas (asr) microns whose faces wind outwards in the atlas's own axes."""
    box = trimesh.creation.box(extents=(size, size, size))
    # trimesh winds outwards in a right-handed frame; the asr frame is used as-is here, so the cube's
    # volume is positive in atlas coordinates.
    return box.vertices + np.asarray(center_asr), box.faces


class FakeAtlas:
    def __init__(self, meshes, version="3.1"):
        self.meshes = meshes  # structure ID or "root" -> (points, faces), or None for no mesh
        self.shape_um = SHAPE_UM
        self.metadata = {"version": version, "name": "allen_mouse"}
        self.structures = {sid: {"acronym": f"S{sid}", "name": f"Structure {sid}"}
                           for sid in meshes if sid != "root"}

    def mesh_from_structure(self, structure):
        mesh = self.meshes[structure]
        if mesh is None:
            return None
        points, faces = mesh
        return SimpleNamespace(points=points, cells=[SimpleNamespace(type="triangle", data=faces)])


ATLAS = {"id": "allen-mouse-ccf-2017", "brainglobe_name": "allen_mouse_25um", "extra": {"brainglobe.atlas_version": "3.1"}}


def test_to_viewer_axes_and_units():
    center, anterior, superior, right = to_viewer(np.array([
        CENTER, CENTER - [1000, 0, 0], CENTER - [0, 1000, 0], CENTER - [0, 0, 1000]]), SHAPE_UM)
    assert center.tolist() == [0, 0, 0]
    assert anterior.tolist() == [0, 0, -1]  # z points posterior
    assert superior.tolist() == [0, 1, 0]   # y points up
    assert right.tolist() == [1, 0, 0]      # x points to the animal's right


def test_convert_keeps_faces_outward():
    points, faces = cube(CENTER)
    mesh = convert(points, faces, SHAPE_UM, max_faces=1000)
    assert mesh.is_winding_consistent and mesh.volume == pytest.approx(1.0)  # 1 mm³, positive: normals point out


def test_convert_simplifies_large_meshes():
    sphere = trimesh.creation.icosphere(subdivisions=4, radius=500)  # 5,120 faces
    mesh = convert(sphere.vertices + CENTER, sphere.faces, SHAPE_UM, max_faces=500)
    assert len(mesh.faces) <= 500 and mesh.volume > 0


def test_right_centroid_uses_the_right_hemisphere():
    points, faces = cube(CENTER, size=2000)  # straddles the midline
    x, y, z = right_centroid(convert(points, faces, SHAPE_UM, 1000))
    assert 0 < x < 1 and y == pytest.approx(0) and z == pytest.approx(0)
    points, faces = cube(CENTER + [0, 0, 3000])  # entirely in the left hemisphere
    assert right_centroid(convert(points, faces, SHAPE_UM, 1000)) == pytest.approx([-3, 0, 0])


def test_export_atlas_writes_meshes_and_index(tmp_path):
    atlas = FakeAtlas({"root": cube(CENTER, 8000), 295: cube(CENTER + [500, 2000, -2000]), 536: None})
    index = export_atlas(ATLAS, ["MBA:295", "MBA:536"], tmp_path, open_atlas=lambda name, version: atlas)
    folder = tmp_path / "allen-mouse-ccf-2017"
    assert json.loads((folder / "index.json").read_text(encoding="utf-8")) == index
    assert index["root"] == "root.glb" and (folder / "root.glb").is_file()
    assert list(index["regions"]) == ["MBA:295"]  # 536 has no mesh in the atlas, so it isn't drawn
    region = index["regions"]["MBA:295"]
    assert region["file"] == "295.glb" and region["acronym"] == "S295" and region["name"] == "Structure 295"
    assert region["centroid"] == pytest.approx([2, -2, 0.5])
    loaded = trimesh.load(folder / "295.glb", force="mesh")
    assert len(loaded.faces) == 12 and loaded.volume == pytest.approx(1.0)


def test_export_atlas_checks_the_pin(tmp_path):
    atlas = FakeAtlas({"root": cube(CENTER)}, version="3.0")
    with pytest.raises(ValueError, match="pins"):
        export_atlas(ATLAS, [], tmp_path, open_atlas=lambda name, version: atlas)


def claim(subject, object_, atlas="allen-mouse-ccf-2017"):
    return Record(path=None, cls="ConnectivityClaim", data={
        "subject": {"type": "region", "id": subject, "atlas": atlas},
        "object": {"type": "region", "id": object_, "atlas": atlas}})


def test_regions_to_draw_takes_the_regions_of_connections():
    loaded = {"allen-mouse-ccf-2017": [{"id": "MBA:295"}, {"id": "MBA:536"}, {"id": "MBA:672"}],
              "allen-human-3d-2020": [{"id": "DHBA:10361"}]}
    drawn = regions_to_draw([claim("MBA:295", "MBA:672"), claim("MBA:295", "MBA:1")], loaded)
    # Atlases with no connections are not drawn; regions outside the loaded atlas never are.
    assert drawn == {"allen-mouse-ccf-2017": ["MBA:295", "MBA:672"]}


def test_build_writes_meshes_for_connections(valid_tree, tmp_path, capsys):
    atlas = FakeAtlas({"root": cube(CENTER, 8000), **{int(i.split(":")[1]): cube(CENTER) for i in USED}})
    brain = tmp_path / "brain"
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--meshes", str(brain)],
                atlas_loader=fake_loader(), amygdala_loader=amygdala_loader, connectivity_loader=no_claims,
                mesh_opener=lambda name, version: atlas) == 0
    index = json.loads((brain / "allen-mouse-ccf-2017" / "index.json").read_text(encoding="utf-8"))
    assert "MBA:295" in index["regions"] and len(index["regions"]) > 1 and "meshes:" in capsys.readouterr().out


def test_meshes_need_the_atlases(valid_tree, tmp_path, capsys):
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--no-atlases",
                 "--meshes", str(tmp_path / "brain")]) == 1
    assert "--meshes needs the atlases" in capsys.readouterr().out and not (tmp_path / "brain").exists()
