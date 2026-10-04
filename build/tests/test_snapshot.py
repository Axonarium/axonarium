"""The site's snapshot (ADR 0017): every row the database gets, so the site can serve them when the database can't."""

import json

from build.tables import TABLES
from build.tests.test_connectivity import build, claim


def test_snapshot_holds_what_the_database_gets(valid_tree, tmp_path):
    target = tmp_path / "site" / "snapshot.json"
    assert build(valid_tree, tmp_path / "dist", "--snapshot", str(target)) == 0
    snapshot = json.loads(target.read_text(encoding="utf-8"))
    assert list(snapshot["tables"]) == list(TABLES)
    tables = snapshot["tables"]
    # Unlike the dumps, it holds the build-time Allen claims and the atlases' regions.
    assert any(row["id"] == "clm-a0a0a0a0a0" for row in tables["connectivity_claims"])
    assert any(row["id"] == "MBA:1105" for row in tables["regions"])  # from the atlas, not the files
    assert tables["edges"] and all(set(row) == {c.name for c in TABLES["edges"].columns} for row in tables["edges"])
    assert snapshot["schema_version"] == json.loads((tmp_path / "dist" / "manifest.json").read_text())["schema_version"]


def test_snapshot_is_written_only_when_the_build_passes(valid_tree, tmp_path):
    target = tmp_path / "snapshot.json"
    assert build(valid_tree, tmp_path / "dist", "--snapshot", str(target), claims=(claim(unit="ms"),)) == 1
    assert not target.exists()


def test_snapshot_without_atlases(valid_tree, tmp_path):
    target = tmp_path / "snapshot.json"
    assert build(valid_tree, tmp_path / "dist", "--no-atlases", "--snapshot", str(target)) == 0
    tables = json.loads(target.read_text(encoding="utf-8"))["tables"]
    assert not any(row["id"] == "MBA:1105" for row in tables["regions"]) and len(tables["connectivity_claims"]) == 15
