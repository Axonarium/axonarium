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


ODD_INPUTS = {
    "unhashable-key": (b"? [a, b]\n: 1\nid: clm-pq22bk4dtz\n", {"yaml-error"}),
    "not-utf8": (b"id: clm-pq22bk4dtz\nparaphrase: \xff\xfe\n", {"yaml-error"}),
    "recursive-alias": (b"id: clm-pq22bk4dtz\nextra: &a {x.y: *a}\n", {"yaml-error"}),
    "any-alias": (b"id: &i clm-pq22bk4dtz\nalso: *i\n", {"yaml-error"}),
    "list-quantity": (None, {"schema"}),
    "huge-int": (None, {"unit"}),
    "list-atlas": (None, {"schema"}),
}


@pytest.mark.parametrize("case", sorted(ODD_INPUTS))
def test_odd_input_is_reported_not_raised(valid_tree, case):
    raw, expected = ODD_INPUTS[case]
    path = valid_tree / "claims" / "examples" / "clm-pq22bk4dtz.yaml"
    if raw is not None:
        path.write_bytes(raw)
    else:
        text = path.read_text()
        text = {"list-quantity": text.replace("quantity: projection_density", "quantity: [projection_density]"),
                "huge-int": text.replace("value: 0.12", "value: " + "9" * 400),
                "list-atlas": text.replace("  atlas: allen-mouse-ccf-2017\npredicate", "  atlas: [allen-mouse-ccf-2017]\npredicate")}[case]
        path.write_text(text, encoding="utf-8")
    assert {f.rule for f in run_files(valid_tree)} == expected


def test_symlinks_are_reported(valid_tree):
    (valid_tree / "claims" / "examples" / "link.yaml").symlink_to("/nonexistent/clm.yaml")
    assert {f.rule for f in run_files(valid_tree)} == {"symlink"}
