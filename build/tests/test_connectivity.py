"""Build-time Allen connectivity claims: checked like committed claims, in the database rows, never in the dumps."""

import json
import os

import psycopg
import pytest

from build.cli import main
from build.tests.test_regions import amygdala_loader, fake_loader

TEST_URL = os.environ.get("AXONARIUM_TEST_DATABASE_URL")


def claim(cid="clm-a0a0a0a0a0", target="MBA:536", unit="1"):
    return {"id": cid, "subject": {"type": "region", "id": "MBA:295", "atlas": "allen-mouse-ccf-2017"},
            "predicate": "projects_to", "object": {"type": "region", "id": target, "atlas": "allen-mouse-ccf-2017"},
            "species": "NCBITaxon:10090", "evidence_class": "anterograde_tracer", "result": "present", "sign": "unknown",
            "measurements": [{"quantity": "projection_density", "value": 0.2, "unit": unit}],
            "source": {"doi": "10.5555/axonarium.example.001", "locator": "Allen Mouse Brain Connectivity Atlas, experiment 1"},
            "paraphrase": "Test fixture: a generated claim.",
            "curation": {"by": "agent", "role": "ingester", "model": "deterministic-adapter", "prompt": "allen-connectivity@1.0.0",
                         "date": "2026-10-03"},
            "status": "accepted", "extra": {"allen.experiment": 1}}


def connectivity(*claims):
    def load(atlas, structure_ids, acronyms):
        assert atlas == "allen-mouse-ccf-2017" and 295 in structure_ids and acronyms[295] == "295"
        return list(claims)
    return load


def build(tree, out, *extra, claims=(claim(),)):
    return main(["--data", str(tree), "--out", str(out), *extra], atlas_loader=fake_loader(),
                amygdala_loader=amygdala_loader, connectivity_loader=connectivity(*claims))


def test_generated_claims_not_in_dumps(valid_tree, tmp_path, capsys):
    assert build(valid_tree, tmp_path / "dist") == 0
    assert "allen connectivity: 1 experiment(s), 1 claim(s)" in capsys.readouterr().out
    dumped = json.loads((tmp_path / "dist" / "axonarium.json").read_text(encoding="utf-8"))
    assert not any((c.get("extra") or {}).get("allen.experiment") for c in dumped["connectivity_claims"])


def test_invalid_generated_claim_stops_build(valid_tree, tmp_path, capsys):
    assert build(valid_tree, tmp_path / "dist", claims=(claim(unit="ms"),)) == 1
    printed = capsys.readouterr().out
    assert "unit" in printed and "allen-connectivity/clm-a0a0a0a0a0.yaml" in printed and not (tmp_path / "dist").exists()


def test_generated_claim_with_unknown_region_stops_build(valid_tree, tmp_path, capsys):
    assert build(valid_tree, tmp_path / "dist", claims=(claim(target="MBA:999999"),)) == 1
    assert "unknown-region" in capsys.readouterr().out


@pytest.mark.skipif(not TEST_URL, reason="needs AXONARIUM_TEST_DATABASE_URL")
def test_generated_claims_reach_the_database_and_rerun_is_identical(valid_tree, tmp_path, monkeypatch):
    monkeypatch.setenv("AXONARIUM_DATABASE_URL", TEST_URL)

    def snapshot():
        with psycopg.connect(TEST_URL) as conn:
            return (conn.execute("select id, subject_id, object_id, measurements from connectivity_claims order by id").fetchall(),
                    conn.execute("select * from edges order by id").fetchall())

    assert build(valid_tree, tmp_path / "a") == 0
    first = snapshot()
    assert any(row[0] == "clm-a0a0a0a0a0" for row in first[0])
    assert build(valid_tree, tmp_path / "b") == 0
    assert snapshot() == first
