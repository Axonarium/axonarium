"""The command: `python -m build [--data data] [--out dist] [--database URL]`."""

import json
import os

import psycopg
import pytest

from build.cli import main
from checks.tests.conftest import BROKEN, overlay

TEST_URL = os.environ.get("AXONARIUM_TEST_DATABASE_URL")


def test_build_valid_tree(valid_tree, tmp_path, capsys):
    out = tmp_path / "dist"
    assert main(["--data", str(valid_tree), "--out", str(out)]) == 0
    assert (out / "axonarium.json").exists() and (out / "edges.csv").exists()
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1 and lines[0].startswith(f"built {out}:") and "connectivity_claims" in lines[0]


def test_build_stops_on_findings(valid_tree, tmp_path, capsys):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "manifest.json").write_text("{}\n", encoding="utf-8")  # a previous build's dumps
    overlay(valid_tree, BROKEN / "schema")
    assert main(["--data", str(valid_tree), "--out", str(out)]) == 1
    output = capsys.readouterr().out
    assert ": schema: " in output and "build stopped" in output
    assert [p.name for p in out.iterdir()] == ["manifest.json"]


def test_build_empty_data(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "retractions.yaml").write_text("entries: []\n", encoding="utf-8")
    assert main(["--data", str(data), "--out", str(tmp_path / "dist")]) == 0
    manifest = json.loads((tmp_path / "dist" / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["tables"].values()) == {0}


def test_not_a_data_folder(tmp_path, capsys):
    assert main(["--data", str(tmp_path / "dta"), "--out", str(tmp_path / "dist")]) == 1
    assert "not a data folder" in capsys.readouterr().out and not (tmp_path / "dist").exists()


def test_database_url_not_printed(valid_tree, tmp_path, capsys):
    url = "postgresql://axonarium:hunter2-secret@127.0.0.1:1/nowhere?connect_timeout=2"
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--database", url]) == 1
    captured = capsys.readouterr()
    assert "hunter2-secret" not in captured.out + captured.err and "rolled back" in captured.out


@pytest.mark.skipif(not TEST_URL, reason="needs AXONARIUM_TEST_DATABASE_URL")
def test_database_from_environment(valid_tree, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AXONARIUM_DATABASE_URL", TEST_URL)
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")]) == 0
    assert "loaded the database" in capsys.readouterr().out
    with psycopg.connect(TEST_URL) as conn:
        assert conn.execute("select count(*) from connectivity_claims").fetchone()[0] > 0


def test_tests_never_see_a_database_url():
    # An exported AXONARIUM_DATABASE_URL must never receive the test fixtures (it may be production).
    assert "AXONARIUM_DATABASE_URL" not in os.environ


@pytest.mark.parametrize("out", [".", "data", "data/dumps", ".."], ids=["working-folder", "data", "inside-data", "parent"])
def test_out_folder_must_be_safe(valid_tree, tmp_path, monkeypatch, capsys, out):
    work = tmp_path / "work"
    work.mkdir()
    (work / "data").symlink_to(valid_tree, target_is_directory=True)
    (work / "keep.txt").write_text("keep\n", encoding="utf-8")
    monkeypatch.chdir(work)
    assert main(["--data", "data", "--out", out]) == 1
    assert "refusing to write dumps" in capsys.readouterr().out
    assert (work / "keep.txt").exists() and (valid_tree / "retractions.yaml").exists()


def test_out_folder_with_other_files_refused(valid_tree, tmp_path, capsys):
    out = tmp_path / "notes"
    out.mkdir()
    (out / "mine.txt").write_text("mine\n", encoding="utf-8")
    assert main(["--data", str(valid_tree), "--out", str(out)]) == 1
    assert "refusing to write dumps" in capsys.readouterr().out and (out / "mine.txt").exists()


def test_previous_build_replaced(valid_tree, tmp_path):
    out = tmp_path / "dist"
    assert main(["--data", str(valid_tree), "--out", str(out)]) == 0
    assert main(["--data", str(valid_tree), "--out", str(out)]) == 0
