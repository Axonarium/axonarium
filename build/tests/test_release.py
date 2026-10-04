"""Packaging a release: the dumps zip, its checksum and the release notes (ADR 0016)."""

import hashlib
import zipfile

import pytest

from build.cli import main as build
from build.release import main, package

COMMIT = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture
def dist(valid_tree, tmp_path):
    out = tmp_path / "dist"
    assert build(["--data", str(valid_tree), "--out", str(out), "--no-atlases"]) == 0
    return out


def test_package_holds_the_dumps_licence_and_readme(dist, tmp_path):
    files = package(dist, tmp_path / "release", "v2026.10.0", COMMIT)
    assert [f.name for f in files] == ["axonarium-v2026.10.0-dumps.zip", "SHA256SUMS"]
    with zipfile.ZipFile(files[0]) as archive:
        names = archive.namelist()
        readme = archive.read("axonarium-v2026.10.0/README.md").decode()
    assert all(name.startswith("axonarium-v2026.10.0/") for name in names)
    assert {f"axonarium-v2026.10.0/{p.name}" for p in dist.iterdir()} | {
        "axonarium-v2026.10.0/LICENSE.txt", "axonarium-v2026.10.0/README.md"} == set(names)
    assert COMMIT in readme and "CC BY 4.0" in readme and "| connectivity_claims | 15 |" in readme


def test_checksum_file_matches_the_zip(dist, tmp_path):
    zipped, sums = package(dist, tmp_path / "release", "v2026.10.0", COMMIT)
    digest = hashlib.sha256(zipped.read_bytes()).hexdigest()
    assert sums.read_text() == f"{digest}  {zipped.name}\n"  # the format `sha256sum -c` reads


def test_same_dumps_give_the_same_zip(dist, tmp_path):
    first = package(dist, tmp_path / "a", "v2026.10.0", COMMIT)[0].read_bytes()
    second = package(dist, tmp_path / "b", "v2026.10.0", COMMIT)[0].read_bytes()
    assert first == second


def test_notes_name_the_version_commit_and_counts(dist, tmp_path):
    package(dist, tmp_path / "release", "v2026.10.0", COMMIT)
    notes = (tmp_path / "release" / "NOTES.md").read_text()
    assert notes.startswith("Axonarium v2026.10.0: the knowledge base at commit 0123456")
    assert "| connectivity_claims | 15 |" in notes and "Allen" in notes and "Zenodo" in notes


@pytest.mark.parametrize("version", ["2026.10.0", "v2026.13.0", "v2026.1.0", "v2026.10.01", "v1.2.3", "v2026.10.0\n"])
def test_bad_versions_refused(dist, tmp_path, version, capsys):
    assert main([version, "--commit", COMMIT, "--dist", str(dist), "--out", str(tmp_path / "release")]) == 1
    assert "vYYYY.MM.N" in capsys.readouterr().out and not (tmp_path / "release").exists()


def test_refuses_a_folder_that_isnt_dumps(tmp_path, capsys):
    (tmp_path / "dist").mkdir()
    assert main(["v2026.10.0", "--commit", COMMIT, "--dist", str(tmp_path / "dist"), "--out", str(tmp_path / "r")]) == 1
    assert "manifest.json" in capsys.readouterr().out


def test_cli_writes_the_release(dist, tmp_path, capsys):
    assert main(["v2026.10.0", "--commit", COMMIT, "--dist", str(dist), "--out", str(tmp_path / "release")]) == 0
    assert sorted(p.name for p in (tmp_path / "release").iterdir()) == [
        "NOTES.md", "SHA256SUMS", "axonarium-v2026.10.0-dumps.zip"]
