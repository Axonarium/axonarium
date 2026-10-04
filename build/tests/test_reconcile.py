"""The reconciliation report (sprint 1.6): agreement, conflict and silence between sources, never resolved."""

import json

import pytest

from build.reconcile import THRESHOLDS, reconcile, write_report
from build.tests.test_connectivity import build

ATLAS = "allen-mouse-ccf-2017"
ALLEN = {"doi": "10.1038/nature13186"}
PAPER = {"doi": "10.5555/axonarium.example.001"}


def region(number: int, acronym: str, parent: int | None = None, amygdala: bool = False) -> dict:
    return {"id": f"MBA:{number}", "acronym": acronym, "name": acronym, "atlas": ATLAS,
            "parent": f"MBA:{parent}" if parent else None, "amygdala": amygdala}


# BLA (295) and CEA (536) are amygdala regions; BLAa (303) is a subdivision of BLA; CP and PL are not.
REGIONS = [region(295, "BLA", amygdala=True), region(303, "BLAa", parent=295), region(536, "CEA", amygdala=True),
           region(672, "CP"), region(972, "PL")]


def claim(subject: int, target: int, density: float | None = None, *, source=ALLEN, locator="experiment 1",
          result="present", status="accepted", prompt="allen-connectivity@1.2.0", role="ingester") -> dict:
    return {"subject": {"type": "region", "id": f"MBA:{subject}", "atlas": ATLAS}, "predicate": "projects_to",
            "object": {"type": "region", "id": f"MBA:{target}", "atlas": ATLAS}, "species": "NCBITaxon:10090",
            "result": result, "status": status, "source": {**source, "locator": locator},
            "measurements": [] if density is None else [{"quantity": "projection_density", "value": density, "unit": "1"}],
            "curation": {"by": "agent", "role": role, "prompt": prompt}}


def paper(subject: int, target: int, result: str = "present", locator: str = "Fig. 1") -> dict:
    return claim(subject, target, source=PAPER, locator=locator, result=result, prompt="extract@1.0.0", role="extractor")


def test_one_source_is_replicated_or_seen_once():
    report = reconcile([claim(295, 672, 0.3, locator="experiment 1"), claim(295, 672, 0.1, locator="experiment 2"),
                        claim(295, 972, 0.02)], REGIONS)
    assert report["categories"] == {"agreement": 0, "conflict": 0, "replicated": 1, "single": 1}
    assert report["sources"] == [{"name": "allen-connectivity", "claims": 3, "connections": 2, "observations": 2}]


def test_sources_agree_or_conflict_and_conflicts_are_listed_not_resolved():
    report = reconcile([claim(295, 672, 0.3), paper(295, 672), claim(295, 536, 0.2), paper(295, 536, "absent")], REGIONS)
    assert report["categories"] == {"agreement": 1, "conflict": 1, "replicated": 0, "single": 0}
    [conflict] = report["conflicts"]
    assert conflict["connection"] == "MBA:295|projects_to|MBA:536|NCBITaxon:10090"
    assert conflict["results"] == {"allen-connectivity": ["present"], "literature": ["absent"]}


def test_retracted_claims_are_left_out():
    report = reconcile([claim(295, 672, 0.3), paper(295, 672, "absent") | {"status": "retracted"}], REGIONS)
    assert report["categories"]["conflict"] == 0 and report["connections"] == 1


def test_outputs_and_inputs_of_the_amygdala_are_counted_apart():
    report = reconcile([claim(295, 672, 0.3), claim(303, 972, 0.2), claim(972, 536, 0.05), claim(672, 972, 0.4)], REGIONS)
    assert {group: sum(counts.values()) for group, counts in report["by_direction"].items()} == {
        "outputs": 2, "inputs": 1, "other": 1}  # BLAa is in the amygdala through its parent


def test_thresholds_count_connections_and_replication():
    report = reconcile([claim(972, 536, 0.03, locator="experiment 1"), claim(972, 536, 0.06, locator="experiment 2"),
                        claim(672, 295, 0.012)], REGIONS)
    inputs = {row["min"]: (row["connections"], row["replicated"]) for row in report["thresholds"]["inputs"]}
    assert list(inputs) == list(THRESHOLDS)
    assert inputs[0.01] == (2, 1) and inputs[0.02] == (1, 1) and inputs[0.05] == (1, 0) and inputs[0.1] == (0, 0)


def test_silence_lists_amygdala_regions_no_claim_names():
    report = reconcile([claim(295, 672, 0.3), claim(972, 295, 0.1)], REGIONS)
    assert report["silence"] == {"amygdala_regions": 3, "without_outputs": ["BLAa", "CEA"], "without_inputs": ["BLAa", "CEA"],
                                 "without_either": ["BLAa", "CEA"]}


def test_without_atlas_regions_there_is_no_silence_section():
    assert reconcile([paper(295, 672)], [])["silence"] is None


def test_report_files(tmp_path):
    report = reconcile([claim(295, 672, 0.3), paper(295, 536, "absent"), claim(295, 536, 0.2)], REGIONS)
    write_report(report, tmp_path / "report")
    assert sorted(p.name for p in (tmp_path / "report").iterdir()) == ["reconciliation.json", "reconciliation.md", "reconciliation.svg"]
    assert json.loads((tmp_path / "report" / "reconciliation.json").read_text()) == report
    markdown = (tmp_path / "report" / "reconciliation.md").read_text()
    assert markdown.startswith("# Reconciliation") and "| Conflict | 1 |" in markdown and "BLAa" in markdown
    assert (tmp_path / "report" / "reconciliation.svg").read_text().lstrip().startswith("<?xml")


def test_report_files_are_reproducible(tmp_path):
    report = reconcile([claim(295, 672, 0.3)], REGIONS)
    write_report(report, tmp_path / "a")
    write_report(report, tmp_path / "b")
    assert all((tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
               for name in ("reconciliation.json", "reconciliation.md", "reconciliation.svg"))


@pytest.mark.parametrize("extra", [[], ["--no-atlases"]])
def test_build_writes_the_report(valid_tree, tmp_path, extra):
    assert build(valid_tree, tmp_path / "dist", "--report", str(tmp_path / "report"), *extra) == 0
    report = json.loads((tmp_path / "report" / "reconciliation.json").read_text())
    names = {source["name"] for source in report["sources"]}
    assert "literature" in names and ("allen-connectivity" in names) == (not extra)
