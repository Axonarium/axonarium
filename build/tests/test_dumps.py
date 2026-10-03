"""Rows for every table, and the dumps written from them."""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from linkml.validator import validate

from build.dumps import write_dumps
from build.tables import CLASS_TABLES, TABLES, columns, rows
from checks.loading import load_tree

SCHEMA = str(Path(__file__).resolve().parents[2] / "schema" / "axonarium.yaml")


def build_rows(data: Path):
    records, findings = load_tree(data)
    assert findings == []
    return records, rows(records)


def test_rows_cover_every_record(valid_tree):
    records, tables = build_rows(valid_tree)
    assert list(tables) == list(TABLES)
    for cls, table in CLASS_TABLES.items():
        assert len(tables[table]) == sum(r.cls == cls for r in records), table
    claim = next(r for r in tables["connectivity_claims"] if r["id"] == "clm-pq22bk4dtz")
    assert (claim["subject_id"], claim["subject_atlas"], claim["object_id"], claim["source_key"], claim["locator"]) == (
        "MBA:295", "allen-mouse-ccf-2017", "MBA:559", "doi:10.5555/axonarium.example.001", "Fig. 3B")
    assert claim["measurements"][0]["quantity"] == "projection_density" and claim["extra"]["lab.tracer"] == "AAV-hSyn-EGFP"
    assert all(set(row) == set(columns(name)) for name, table in tables.items() for row in table)


def test_knowledge_base_validates(valid_tree, tmp_path):
    records, tables = build_rows(valid_tree)
    write_dumps(records, tables, tmp_path / "dist")
    kb = json.loads((tmp_path / "dist" / "axonarium.json").read_text(encoding="utf-8"))
    report = validate(kb, SCHEMA, "KnowledgeBase")
    assert [r.message for r in report.results if getattr(r.severity, "name", r.severity) == "ERROR"] == []
    assert len(kb["connectivity_claims"]) == len(tables["connectivity_claims"])


def test_csv_round_trip_awkward_text(valid_tree, tmp_path):
    path = valid_tree / "claims" / "examples" / "clm-pq22bk4dtz.yaml"
    awkward = 'Quote " comma , newline\nand é'
    path.write_text(path.read_text(encoding="utf-8").replace(
        "paraphrase: >-\n  Illustrative example: an anterograde tracer injected into the basolateral\n"
        "  amygdalar nucleus labelled axon terminals in the medial part of the central\n  amygdalar nucleus.\n",
        f"paraphrase: {json.dumps(awkward)}\n"), encoding="utf-8")
    records, tables = build_rows(valid_tree)
    write_dumps(records, tables, tmp_path / "dist")
    with open(tmp_path / "dist" / "connectivity_claims.csv", encoding="utf-8", newline="") as f:
        read = list(csv.DictReader(f))
    assert len(read) == len(tables["connectivity_claims"])
    assert next(r for r in read if r["id"] == "clm-pq22bk4dtz")["paraphrase"] == awkward
    assert json.loads(read[0]["curation"])["date"]  # JSON parts are JSON text


def test_graphml_parses(valid_tree, tmp_path):
    records, tables = build_rows(valid_tree)
    write_dumps(records, tables, tmp_path / "dist")
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    graph = ET.parse(tmp_path / "dist" / "edges.graphml").getroot().find("g:graph", ns)
    nodes = {e["subject_id"] for e in tables["edges"]} | {e["object_id"] for e in tables["edges"]}
    assert len(graph.findall("g:node", ns)) == len(nodes)
    assert len(graph.findall("g:edge", ns)) == len(tables["edges"])


def test_dumps_deterministic(valid_tree, tmp_path):
    records, tables = build_rows(valid_tree)
    write_dumps(records, tables, tmp_path / "a")
    write_dumps(*build_rows(valid_tree), tmp_path / "b")
    names = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert names == sorted(p.name for p in (tmp_path / "b").iterdir())
    assert all((tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes() for n in names)


def test_manifest_counts(valid_tree, tmp_path):
    records, tables = build_rows(valid_tree)
    write_dumps(records, tables, tmp_path / "dist")
    manifest = json.loads((tmp_path / "dist" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "0.2.1"
    assert manifest["tables"] == {name: len(table) for name, table in tables.items()}


def test_replaces_out_folder(valid_tree, tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "stale.csv").write_text("old\n", encoding="utf-8")
    write_dumps(*build_rows(valid_tree), out)
    assert not (out / "stale.csv").exists() and (out / "axonarium.json").exists()


def test_unknown_field_is_an_error(valid_tree):
    records, _ = load_tree(valid_tree)
    claim = next(r for r in records if r.cls == "ConnectivityClaim")
    claim.data["new_slot"] = "x"
    with pytest.raises(ValueError, match="new_slot"):
        rows(records)


def test_unknown_citation_field_is_an_error(valid_tree):
    records, _ = load_tree(valid_tree)
    claim = next(r for r in records if r.cls == "ConnectivityClaim")
    claim.data["source"]["page"] = "12"
    with pytest.raises(ValueError, match="source.page"):
        rows(records)


def test_every_schema_slot_has_a_column():
    from linkml_runtime.utils.schemaview import SchemaView

    view = SchemaView(SCHEMA)
    nested = {"subject": ("subject_", "EntityRef"), "object": ("object_", "EntityRef"), "region": ("region_", "EntityRef")}
    for cls, table in CLASS_TABLES.items():
        known = set(columns(table))
        for slot in view.class_slots(cls):
            if slot in nested:
                prefix, ref = nested[slot]
                missing = {f"{prefix}{s}" for s in view.class_slots(ref)} - known
            elif slot == "source":
                missing = set(view.class_slots("Citation")) - known
            else:
                missing = {slot} - known
            assert not missing, f"{cls}.{slot} has no column in {table}: {missing}"
