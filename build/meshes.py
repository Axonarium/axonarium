"""Region meshes for the site's 3D view, converted from BrainGlobe to glTF at build time (ADR 0011).

Like atlas regions, the meshes are never committed (ADR 0005): the deploy job writes them into the site build.
Coordinates are millimetres from the centre of the atlas volume, with x towards the animal's right, y up and
z posterior, a right-handed frame for three.js.
"""

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import trimesh

from checks.findings import Record
from ingest.atlases import _open_brainglobe

MAX_FACES = 4000  # per region; BrainGlobe's meshes are already light, and most regions stay under this
ROOT_FACES = 20000  # the whole-brain outline, drawn translucent


def to_viewer(points: np.ndarray, shape_um) -> np.ndarray:
    """Atlas points in microns, axes anterior->posterior, superior->inferior, right->left (BrainGlobe's "asr"),
    to viewer millimetres: x right, y superior, z posterior."""
    centred = (np.asarray(points, dtype=float) - np.asarray(shape_um, dtype=float) / 2) / 1000
    return np.column_stack([-centred[:, 2], -centred[:, 1], centred[:, 0]]) + 0.0  # + 0.0 turns -0.0 into 0.0


def convert(points: np.ndarray, triangles: np.ndarray, shape_um, max_faces: int) -> trimesh.Trimesh:
    """One BrainGlobe mesh in viewer coordinates, simplified to at most max_faces triangles."""
    # The axis change mirrors the mesh, so each triangle's corners are reversed to keep its normal pointing out.
    mesh = trimesh.Trimesh(vertices=to_viewer(points, shape_um), faces=np.asarray(triangles)[:, ::-1], process=True)
    if len(mesh.faces) > max_faces:
        mesh = mesh.simplify_quadric_decimation(face_count=max_faces)
    return mesh


def right_centroid(mesh: trimesh.Trimesh) -> list[float]:
    """Where arcs meet a region: the area-weighted centre of its right-hemisphere surface (Allen's injections
    are in the right hemisphere), or of its whole surface if it has none on the right."""
    centres, areas = mesh.triangles_center, mesh.area_faces
    right = centres[:, 0] > 0
    if right.any():
        centres, areas = centres[right], areas[right]
    return [round(float(v), 4) for v in np.average(centres, axis=0, weights=areas)]


def _triangles(brainglobe_mesh) -> tuple[np.ndarray, np.ndarray] | None:
    if brainglobe_mesh is None:
        return None
    faces = [cells.data for cells in brainglobe_mesh.cells if cells.type == "triangle"]
    return (brainglobe_mesh.points, np.concatenate(faces)) if faces else None


def export_atlas(atlas: dict, region_ids: list[str], out: Path, open_atlas: Callable = _open_brainglobe,
                 max_faces: int = MAX_FACES, root_faces: int = ROOT_FACES, amygdala: set[str] = frozenset()) -> dict:
    """Write out/<atlas id>/: root.glb, one <structure>.glb per region with a mesh, and index.json, which marks the
    amygdala's regions (with their subdivisions) so the view can tell its inputs from its outputs. Returns the index."""
    pinned = str(atlas["extra"]["brainglobe.atlas_version"])
    brainglobe = open_atlas(atlas["brainglobe_name"], pinned)
    if str(brainglobe.metadata["version"]) != pinned:
        raise ValueError(f"{atlas['id']} pins BrainGlobe {pinned}, but BrainGlobe served {brainglobe.metadata['version']}")
    folder = out / atlas["id"]
    folder.mkdir(parents=True, exist_ok=True)
    root = _triangles(brainglobe.mesh_from_structure("root"))
    if root is None:
        raise ValueError(f"{atlas['id']}: BrainGlobe has no root mesh")
    convert(*root, brainglobe.shape_um, root_faces).export(folder / "root.glb", file_type="glb", include_normals=True)
    regions = {}
    for region in region_ids:
        structure = int(region.split(":")[1])
        found = _triangles(brainglobe.mesh_from_structure(structure))
        if found is None:
            continue
        mesh = convert(*found, brainglobe.shape_um, max_faces)
        mesh.export(folder / f"{structure}.glb", file_type="glb", include_normals=True)
        info = brainglobe.structures[structure]
        regions[region] = {"acronym": info["acronym"], "name": info["name"], "file": f"{structure}.glb",
                           "centroid": right_centroid(mesh), "amygdala": region in amygdala}
    index = {"atlas": atlas["id"], "units": "mm", "axes": "x right, y superior, z posterior",
             "root": "root.glb", "regions": regions}
    (folder / "index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return index


def regions_to_draw(claims: list[Record], loaded: dict[str, list[dict]]) -> dict[str, list[str]]:
    """Per loaded atlas with connections, the sorted regions those connections name."""
    known = {atlas: {row["id"] for row in rows} for atlas, rows in loaded.items()}
    drawn: dict[str, set[str]] = {}
    for record in claims:
        if record.cls != "ConnectivityClaim":
            continue
        for end in (record.data["subject"], record.data["object"]):
            atlas = end.get("atlas")
            if end.get("type") == "region" and end["id"] in known.get(atlas, ()):
                drawn.setdefault(atlas, set()).add(end["id"])
    return {atlas: sorted(ids, key=lambda i: int(i.split(":")[1])) for atlas, ids in sorted(drawn.items())}
