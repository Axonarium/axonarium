"""The `files` command: the valid tree passes, and each broken fixture fails with its own rule."""

import re
import shutil

import pytest

from checks.cli import main, run_files
from checks.tests.conftest import BROKEN, overlay

FIXTURES = sorted(p for p in BROKEN.iterdir() if p.is_dir())


def test_valid_tree_has_no_findings(valid_tree):
    assert run_files(valid_tree) == []


def test_nested_module_folders(valid_tree):
    nested = valid_tree / "claims" / "amygdala" / "bla"
    nested.mkdir(parents=True)
    shutil.move(valid_tree / "claims" / "examples" / "clm-pq22bk4dtz.yaml", nested / "clm-pq22bk4dtz.yaml")
    assert run_files(valid_tree) == []


def test_ignores_non_yaml(valid_tree):
    (valid_tree / "README.md").write_text("# Data\n", encoding="utf-8")
    (valid_tree / "claims" / "notes.txt").write_text("scratch\n", encoding="utf-8")
    (valid_tree / "claims" / ".DS_Store").write_bytes(b"\x00\x01")
    assert run_files(valid_tree) == []


def test_cli_output_and_exit_status(valid_tree, capsys):
    assert main(["files", "--data", str(valid_tree)]) == 0
    assert capsys.readouterr().out == ""
    overlay(valid_tree, BROKEN / "schema")
    assert main(["files", "--data", str(valid_tree)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines and all(re.match(r"^\S+: [a-z-]+: .+$", line) for line in lines), lines


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_broken_fixture_reports_its_rule(valid_tree, fixture):
    overlay(valid_tree, fixture)
    findings = run_files(valid_tree)
    assert {f.rule for f in findings} == {fixture.name}, [str(f) for f in findings]
