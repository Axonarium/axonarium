"""The `online` command: identifiers and citations looked up in their registries, from replayed responses."""

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml

from checks.change_rules import changed_since
from checks.cli import main, run_files
from checks.http import Fetcher
from checks.loading import load_tree
from checks.lookups import CROSSREF, NCBI, OLS
from checks.online_rules import check_online, mismatched
from checks.tests.conftest import overlay
from checks.tests.test_changes import git

ONLINE = Path(__file__).parent / "fixtures" / "online"
BROKEN_ONLINE = sorted(p for p in (ONLINE / "broken").iterdir() if p.is_dir())
TODAY = date(2026, 10, 3)


@pytest.fixture
def online_tree(tmp_path) -> Path:
    data = tmp_path / "data"
    shutil.copytree(ONLINE / "valid", data)
    return data


def online(data: Path, fetch: Fetcher, scope=None):
    records, _ = load_tree(data)
    return check_online(records, fetch, TODAY, scope)


def test_online_valid_tree(online_tree, fetch):
    assert online(online_tree, fetch) == []
    assert run_files(online_tree) == []


@pytest.mark.parametrize("fixture", BROKEN_ONLINE, ids=lambda p: p.name)
def test_online_broken_fixture(online_tree, fetch, fixture):
    overlay(online_tree, fixture)
    findings = online(online_tree, fetch)
    assert findings and {f.rule for f in findings} == {fixture.name}, [str(f) for f in findings]
    # Every file in the overlay is caught, not just one of them.
    assert {Path(f.path).relative_to(online_tree) for f in findings} == {p.relative_to(fixture) for p in fixture.rglob("*.yaml")}


def test_lookup_failed(online_tree, replay):
    failing = OLS.format(ontology="uberon", curie="UBERON:0002883")

    def opener(url, headers, timeout):
        if url == failing:
            raise OSError("connection reset")
        return replay(url, headers, timeout)

    findings = online(online_tree, Fetcher(None, opener, sleep=lambda seconds: None))
    assert [(Path(f.path).name, f.rule) for f in findings] == [("hom-c643x76f02.yaml", "lookup-failed")]


def test_each_identifier_looked_up_once(online_tree, fetch):
    online(online_tree, fetch)  # MBA:295, MBA:536, the species and the Hintiryan DOI are each used twice
    assert fetch.requested and len(fetch.requested) == len(set(fetch.requested))


def test_pubmed_doi_case_ignored():
    summary = {"articleids": [{"idtype": "doi", "value": "10.1038/S41467-021-22915-5"}]}
    assert mismatched("10.1038/s41467-021-22915-5", summary, "doi") is None
    assert mismatched("10.1038/s41467-021-22856-z", summary, "doi") == "10.1038/S41467-021-22915-5"
    assert mismatched("10.1038/s41467-021-22856-z", {"articleids": []}, "doi") is None


def test_cli_online(online_tree, replay, tmp_path, capsys):
    command = ["online", "--data", str(online_tree), "--cache", str(tmp_path / "cache")]
    assert main(command, opener=replay) == 0
    assert capsys.readouterr().out == ""
    overlay(online_tree, ONLINE / "broken" / "unknown-term")
    assert main(command, opener=replay) == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2 and all(": unknown-term: " in line for line in lines), lines


@pytest.fixture
def online_repo(online_tree) -> Path:
    """The online valid tree committed on main, with a branch checked out for the changes under test."""
    repo = online_tree.parent
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "branch")
    return online_tree


def scoped(data: Path, fetch: Fetcher):
    return online(data, fetch, changed_since(data, "main"))


def test_scope_changed_claim_and_its_source(online_repo, fetch):
    claim = online_repo / "claims" / "examples" / "clm-9dd2wps80g.yaml"
    claim.write_text(claim.read_text(encoding="utf-8").replace("locator: Fig. 2", "locator: Fig. 3"), encoding="utf-8")
    git(online_repo.parent, "commit", "-q", "-am", "change")
    assert scoped(online_repo, fetch) == []
    assert CROSSREF.format(doi="10.1038/s41467-021-22915-5") in fetch.requested  # the cited source is checked too
    assert OLS.format(ontology="uberon", curie="UBERON:0002883") not in fetch.requested
    assert OLS.format(ontology="cl", curie="CL:0000679") not in fetch.requested


def test_scope_nothing_changed(online_repo, fetch, replay, tmp_path):
    assert scoped(online_repo, fetch) == [] and fetch.requested == []
    command = ["online", "--base", "main", "--data", str(online_repo), "--cache", str(tmp_path / "cache")]
    assert main(command, opener=replay) == 0


def test_scope_untracked_file(online_repo, fetch):
    text = (online_repo / "entities" / "neuron_types" / "nt-v2xdcyrdft.yaml").read_text(encoding="utf-8")
    (online_repo / "entities" / "neuron_types" / "nt-2w33dsbbr3.yaml").write_text(
        text.replace("nt-v2xdcyrdft", "nt-2w33dsbbr3").replace("CL:0000679", "CL:0000399"), encoding="utf-8")
    assert {f.rule for f in scoped(online_repo, fetch)} == {"obsolete-term"}


def test_scope_ignores_deleted_files(online_repo, fetch):
    (online_repo / "homology" / "hom-c643x76f02.yaml").unlink()
    assert scoped(online_repo, fetch) == [] and fetch.requested == []


def test_ci_cache_outside_checkout():
    # A pull request could commit forged answers under .cache/; CI must never read a cache from the checkout.
    workflow = yaml.safe_load((Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    runs = [step["run"] for job in workflow["jobs"].values() for step in job["steps"] if "checks online" in step.get("run", "")]
    assert runs and all('--cache "$RUNNER_TEMP/' in run for run in runs), runs


@pytest.mark.parametrize("old, new, rule", [
    ("id: MBA:295\n", "id: MBA:２９５\n", "unknown-term"),
    ("id: MBA:295\n", 'id: "MBA:295\\n"\n', "unknown-term"),
    ('pmid: "34001873"', 'pmid: "034001873"', "unknown-citation"),
    ("pmcid: PMC8129205", "pmcid: PMC08129205", "unknown-citation"),
    ("doi: 10.1038/s41467-021-22915-5", 'doi: "10.1038/s41467-021-22915-5\\n"', "unknown-citation"),
], ids=["full-width-digits", "trailing-newline-term", "pmid-leading-zero", "pmcid-leading-zero", "doi-trailing-newline"])
def test_non_canonical_ids_are_unknown(online_tree, fetch, old, new, rule):
    claim = online_tree / "claims" / "examples" / "clm-9dd2wps80g.yaml"
    text = claim.read_text(encoding="utf-8")
    assert old in text
    claim.write_text(text.replace(old, new, 1), encoding="utf-8")
    findings = [f for f in online(online_tree, fetch) if f.path == str(claim)]
    assert [f.rule for f in findings] == [rule], [str(f) for f in findings]


@pytest.mark.parametrize("url, body", [
    (OLS.format(ontology="uberon", curie="UBERON:0002883"), {"_embedded": None}),
    (OLS.format(ontology="uberon", curie="UBERON:0002883"), {"_embedded": []}),
    (CROSSREF.format(doi="10.1038/s41467-021-22915-5"), {"message": {"updated-by": [{"type": ["retraction"]}]}}),
], ids=["ols-null", "ols-list", "crossref-odd-update"])
def test_odd_registry_answers_are_reported_not_raised(online_tree, replay, url, body):
    def opener(asked, headers, timeout):
        return (200, {}, json.dumps(body).encode()) if asked == url else replay(asked, headers, timeout)

    findings = online(online_tree, Fetcher(None, opener, sleep=lambda seconds: None))
    assert findings and {f.rule for f in findings} == {"lookup-failed"}, [str(f) for f in findings]


def test_pmid_and_pmcid_without_doi(online_tree, replay):
    # Neither record names a DOI, and the PMC record names the cited PMID: nothing to add.
    claim = online_tree / "claims" / "examples" / "clm-2w33dsbbr3.yaml"
    claim.write_text(claim.read_text(encoding="utf-8").replace('  pmid: "1023575"\n', '  pmid: "1023575"\n  pmcid: PMC1\n'), encoding="utf-8")
    pmc = NCBI.format(db="pmc", uid="1")
    summary = {"result": {"uids": ["1"], "1": {"uid": "1", "title": "T", "articleids": [{"idtype": "pmid", "value": "1023575"}]}}}

    def opener(url, headers, timeout):
        return (200, {}, json.dumps(summary).encode()) if url == pmc else replay(url, headers, timeout)

    assert online(online_tree, Fetcher(None, opener, sleep=lambda seconds: None)) == []


def test_scope_includes_pubmed_record(online_tree, fetch):
    # The PubMed record is stale on main; a branch touching only the claim that cites it still checks it.
    record = online_tree / "sources" / "pubmed" / "pubmed_1023575.yaml"
    record.write_text(record.read_text(encoding="utf-8").replace("retracted: false", "retracted: true"), encoding="utf-8")
    repo = online_tree.parent
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    claim = online_tree / "claims" / "examples" / "clm-2w33dsbbr3.yaml"
    claim.write_text(claim.read_text(encoding="utf-8").replace("locator: Fig. 2", "locator: Fig. 3"), encoding="utf-8")
    assert [(Path(f.path).name, f.rule) for f in scoped(online_tree, fetch)] == [("pubmed_1023575.yaml", "source-outdated")]


def test_retracted_pmid_with_unrelated_doi(online_tree, fetch):
    # A real DOI paired with a retracted paper's PMID (PubMed names no DOI for it, so nothing can mismatch).
    claim = online_tree / "claims" / "examples" / "clm-9dd2wps80g.yaml"
    text = claim.read_text(encoding="utf-8").replace('pmid: "34001873"', 'pmid: "11134581"').replace("  pmcid: PMC8129205\n", "")
    claim.write_text(text, encoding="utf-8")
    findings = [f for f in online(online_tree, fetch) if f.path == str(claim)]
    assert [f.rule for f in findings] == ["cites-retracted"], [str(f) for f in findings]


def test_crossref_miss_caught_through_pubmed(online_tree, fetch):
    record = online_tree / "sources" / "doi" / "doi_10.1503_jpn.120073.yaml"
    record.write_text("id: doi:10.1503/jpn.120073\nretracted: false\n", encoding="utf-8")
    findings = [f for f in online(online_tree, fetch) if f.path == str(record)]
    assert any(f.rule == "source-outdated" and "retracted: false" in f.message for f in findings), [str(f) for f in findings]
