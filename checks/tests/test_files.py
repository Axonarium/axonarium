"""The `files` command: the valid tree passes, and each broken fixture fails with its own rule."""

import re
import shutil

import pytest
import yaml

from checks.cli import main, run_files
from checks.identifiers import source_file_name
from checks.tests.conftest import BROKEN, REPO, overlay

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
    "nul-character": (None, {"json-value"}),
    "lone-surrogate": (None, {"json-value"}),
    "number-key": (None, {"json-value"}),
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
                "list-atlas": text.replace("  atlas: allen-mouse-ccf-2017\npredicate", "  atlas: [allen-mouse-ccf-2017]\npredicate"),
                "nul-character": text.replace("locator: Fig. 3B", 'locator: "Fig. 3B\\0"'),
                "lone-surrogate": text.replace("locator: Fig. 3B", 'locator: "Fig. 3B \\ud800"'),
                "number-key": text.replace("    depth_um: 4300", "    depth_um: 4300\n    1: one")}[case]
        path.write_text(text, encoding="utf-8")
    assert {f.rule for f in run_files(valid_tree)} == expected


def test_symlinks_are_reported(valid_tree):
    (valid_tree / "claims" / "examples" / "link.yaml").symlink_to("/nonexistent/clm.yaml")
    assert {f.rule for f in run_files(valid_tree)} == {"symlink"}


def test_excerpt_without_doi(valid_tree):
    path = valid_tree / "claims" / "examples" / "clm-pq22bk4dtz.yaml"
    text = path.read_text(encoding="utf-8")
    assert "  doi: 10.5555/axonarium.example.001\n" in text
    path.write_text(text.replace("  doi: 10.5555/axonarium.example.001\n", '  pmid: "34001873"\n'), encoding="utf-8")
    write_source(valid_tree, "pubmed", {"id": "pubmed:34001873", "title": "A paper without a licence", "kind": "journal_article", "retracted": False})
    assert [f.rule for f in run_files(valid_tree)] == ["excerpt-licence"]


def test_misnamed_source(valid_tree):
    sources = valid_tree / "sources" / "doi"
    (sources / "doi_10.5555_axonarium.example.001.yaml").rename(sources / "example-001.yaml")
    findings = run_files(valid_tree)
    assert [f.rule for f in findings] == ["file-name"]
    assert "doi_10.5555_axonarium.example.001.yaml" in findings[0].message


def write_source(data, scheme: str, record: dict) -> None:
    folder = data / "sources" / scheme
    folder.mkdir(parents=True, exist_ok=True)
    (folder / source_file_name(record["id"])).write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


def cite_pmid_only(data, pmid: str):
    """The bla-to-ceam example, citing only a PubMed ID and without its excerpt."""
    path = data / "claims" / "examples" / "clm-pq22bk4dtz.yaml"
    text = path.read_text(encoding="utf-8").replace("  doi: 10.5555/axonarium.example.001\n", f'  pmid: "{pmid}"\n')
    path.write_text("\n".join(line for line in text.splitlines() if not line.startswith("excerpt:")) + "\n", encoding="utf-8")


def test_pmid_only_claim_needs_record(valid_tree):
    cite_pmid_only(valid_tree, "1023575")
    findings = run_files(valid_tree)
    assert [f.rule for f in findings] == ["missing-source"] and "pubmed:1023575" in findings[0].message


def test_retracted_paper_cited_by_pmid_only(valid_tree):
    cite_pmid_only(valid_tree, "11134581")
    write_source(valid_tree, "pubmed", {"id": "pubmed:11134581", "title": "A retracted paper", "kind": "journal_article", "retracted": True})
    assert [f.rule for f in run_files(valid_tree)] == ["cites-retracted"]


ALLOWLIST = REPO / "data" / "allowlist.yaml"


@pytest.mark.parametrize("server,allowed", [("bioRxiv", True), ("Research Square", False)])
def test_preprints_only_from_listed_servers(valid_tree, server, allowed):
    cite_pmid_only(valid_tree, "1")
    write_source(valid_tree, "pubmed", {"id": "pubmed:1", "journal": server, "kind": "preprint", "retracted": False})
    findings = run_files(valid_tree)  # the example allowlist accepts bioRxiv preprints only
    assert [f.rule for f in findings] == ([] if allowed else ["source-not-allowed"])
    assert allowed or "a preprint from Research Square" in findings[0].message


def test_without_an_allowlist_no_source_is_accepted(valid_tree):
    (valid_tree / "allowlist.yaml").unlink()
    findings = run_files(valid_tree)
    claims = [p for p in valid_tree.rglob("*.yaml") if p.parts[-3:-1] == ("claims", "examples") or p.parent.name == "homology"]
    assert {f.rule for f in findings} == {"source-not-allowed"} and len(findings) == len(claims)


@pytest.mark.parametrize("kind,journal,allowed", [
    ("journal_article", "Neuron", True), ("preprint", "bioRxiv", True), ("preprint", "medRxiv", True),
    ("preprint", "arXiv", True), ("preprint", "SSRN", False), ("dataset", "Zenodo", False), ("other", None, False),
])
def test_the_projects_allowlist(valid_tree, kind, journal, allowed):
    shutil.copy(ALLOWLIST, valid_tree / "allowlist.yaml")
    cite_pmid_only(valid_tree, "1")
    write_source(valid_tree, "pubmed", {"id": "pubmed:1", "journal": journal, "kind": kind, "retracted": False})
    assert [f.rule for f in run_files(valid_tree)] == ([] if allowed else ["source-not-allowed"])
