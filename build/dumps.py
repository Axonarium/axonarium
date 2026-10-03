"""Dumps written from the data: the records as JSON, every table as CSV, the edge graph as GraphML, and a manifest."""

import csv
import io
import json
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from build.tables import columns
from checks.findings import Record

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "axonarium.yaml"
KB_SLOTS = {"ConnectivityClaim": "connectivity_claims", "HomologyClaim": "homology_claims", "Atlas": "atlases",
            "Region": "regions", "NeuronType": "neuron_types", "Source": "sources"}
GRAPHML = "http://graphml.graphdrawing.org/xmlns"
EDGE_KEYS = ("predicate", "species", "n_claims", "n_present", "n_absent", "n_ambiguous", "n_disputed", "strength")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1) + "\n"


def _cell(value) -> str:
    """A CSV cell: arrays and JSON parts as JSON text, booleans as true/false, nulls empty."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _csv(table: str, rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    names = columns(table)
    writer.writerow(names)
    writer.writerows([_cell(row[c]) for c in names] for row in rows)
    return buffer.getvalue()


def _graphml(rows: dict[str, list[dict]]) -> str:
    ET.register_namespace("", GRAPHML)
    root = ET.Element(f"{{{GRAPHML}}}graphml")
    ET.SubElement(root, f"{{{GRAPHML}}}key", {"id": "type", "for": "node", "attr.name": "type", "attr.type": "string"})
    for key in EDGE_KEYS:
        kind = "int" if key.startswith("n_") else "string"
        ET.SubElement(root, f"{{{GRAPHML}}}key", {"id": key, "for": "edge", "attr.name": key, "attr.type": kind})
    graph = ET.SubElement(root, f"{{{GRAPHML}}}graph", {"id": "axonarium", "edgedefault": "directed"})
    nodes = {}
    for edge in rows["edges"]:
        nodes.setdefault(edge["subject_id"], edge["subject_type"])
        nodes.setdefault(edge["object_id"], edge["object_type"])
    for node_id, node_type in sorted(nodes.items()):
        ET.SubElement(ET.SubElement(graph, f"{{{GRAPHML}}}node", {"id": node_id}), f"{{{GRAPHML}}}data", {"key": "type"}).text = node_type
    for edge in rows["edges"]:
        element = ET.SubElement(graph, f"{{{GRAPHML}}}edge", {"id": edge["id"], "source": edge["subject_id"], "target": edge["object_id"]})
        for key in EDGE_KEYS:
            if edge[key] is not None:
                ET.SubElement(element, f"{{{GRAPHML}}}data", {"key": key}).text = str(edge[key])
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"


def write_dumps(records: list[Record], rows: dict[str, list[dict]], out: Path) -> None:
    """Write every dump into a fresh folder, then put it in place of `out`."""
    kb = {slot: sorted((r.data for r in records if r.cls == cls), key=lambda d: d["id"]) for cls, slot in KB_SLOTS.items()}
    log = next((r.data for r in records if r.cls == "RetractionLog"), {"entries": []})
    files = {
        "axonarium.json": _json(kb),
        "retractions.json": _json(log),
        "edges.graphml": _graphml(rows),
        "manifest.json": _json({"schema_version": str(yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))["version"]),
                                "tables": {name: len(table) for name, table in rows.items()}}),
        **{f"{name}.csv": _csv(name, table) for name, table in rows.items()},
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fresh = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        for name, text in files.items():
            (fresh / name).write_text(text, encoding="utf-8", newline="")
        if out.exists():
            shutil.rmtree(out)
        fresh.rename(out)
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
