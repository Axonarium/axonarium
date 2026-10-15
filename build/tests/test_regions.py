"""Atlas regions in the build: merged into the database rows, checked against data, kept out of the dumps."""

import json

from build.cli import main
from checks.tests.conftest import overlay  # noqa: F401
from ingest.atlases import AtlasPinMismatch

# Every MBA region the valid tree's claims and neuron types name, so a fake atlas can hold them all.
USED = ["MBA:1105", "MBA:131", "MBA:194", "MBA:295", "MBA:382", "MBA:403", "MBA:44", "MBA:536", "MBA:551", "MBA:559",
        "MBA:56", "MBA:693", "MBA:703", "MBA:795", "MBA:867", "MBA:972"]


AMYGDALA = {"UBERON:0001876": "amygdala", "UBERON:0002887": "basal amygdaloid nucleus"}
# The valid tree's modules.yaml (schema/examples/valid/ModuleList-example.yaml) names these roots.
TERMS = {"UBERON:0001876": AMYGDALA, "UBERON:0000451": {"UBERON:0000451": "prefrontal cortex"}}


def terms_loader(roots):
    assert roots == list(TERMS)
    return TERMS


def no_claims(atlas, structure_ids, acronyms):
    return []


def fake_loader(ids=USED, amygdala="MBA:295", empty=()):
    def load(atlas, terms):
        assert terms == TERMS
        if atlas["id"] in empty:
            return []
        return [{"id": i, "name": f"Region {i}", "acronym": i.split(":")[1], "atlas": atlas["id"], "parent": None,
                 "uberon": "UBERON:0002887" if i == amygdala else None, "amygdala": i == amygdala,
                 "uberon_label": "basal amygdaloid nucleus" if i == amygdala else None, "synonyms": None, "extra": None}
                for i in ids]
    return load


def test_atlas_regions_reach_the_database_rows_not_the_dumps(valid_tree, tmp_path, capsys):
    out = tmp_path / "dist"
    assert main(["--data", str(valid_tree), "--out", str(out)], atlas_loader=fake_loader(), terms_loader=terms_loader,
                connectivity_loader=no_claims) == 0
    printed = capsys.readouterr().out
    assert "allen-mouse-ccf-2017: 16 regions" in printed and "amygdala" in printed
    dumped = json.loads((out / "axonarium.json").read_text(encoding="utf-8"))
    assert not any(r["name"].startswith("Region MBA:") for r in dumped["regions"])  # atlas-derived names stay out (ADR 0005)
    assert "Region MBA:295" not in (out / "regions.csv").read_text(encoding="utf-8")


def test_unknown_region_stops_build(valid_tree, tmp_path, capsys):
    loader = fake_loader([i for i in USED if i != "MBA:559"])
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=loader, terms_loader=terms_loader) == 1
    printed = capsys.readouterr().out
    assert "unknown-region" in printed and "MBA:559" in printed and "allen-mouse-ccf-2017" in printed


def test_no_atlases_skips_loading(valid_tree, tmp_path):
    def refuse(*args):
        raise AssertionError("atlases must not load with --no-atlases")
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--no-atlases"], atlas_loader=refuse, terms_loader=refuse) == 0


def test_pin_mismatch_reported(valid_tree, tmp_path, capsys):
    def mismatched(atlas, terms):
        raise AtlasPinMismatch("allen-mouse-ccf-2017 pins 3.1, but BrainGlobe serves 3.2")
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=mismatched, terms_loader=terms_loader) == 1
    assert "BrainGlobe serves 3.2" in capsys.readouterr().out


def test_atlas_without_amygdala_stops_build(valid_tree, tmp_path, capsys):
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=fake_loader(amygdala=None), terms_loader=terms_loader) == 1
    assert "no amygdala regions" in capsys.readouterr().out


def test_region_ids_checked_in_atlases_without_regions(valid_tree, tmp_path, capsys):
    # The example atlas, loaded with no regions (like Waxholm), can't hold MBA:295 or any other region ID.
    loader = fake_loader(empty=("allen-mouse-ccf-2017",))
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=loader, terms_loader=terms_loader) == 1
    assert "unknown-region" in capsys.readouterr().out


def test_no_atlases_refuses_a_database(valid_tree, tmp_path, capsys):
    # Loading without atlases would empty the live regions table.
    argv = ["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--no-atlases", "--database", "postgresql://x@127.0.0.1:1/x"]
    assert main(argv) == 1
    assert "--no-atlases" in capsys.readouterr().out and not (tmp_path / "dist").exists()


def test_merge_adds_atlas_regions_to_the_database_rows():
    from build.regions import merge

    tables = {"regions": [{"id": "MBA:1", "name": "from a file"}], "atlases": []}
    merged = merge(tables, {"a": [{"id": "MBA:1", "name": "from the atlas"}, {"id": "MBA:2", "name": "atlas only"}]})
    assert [r["name"] for r in merged["regions"]] == ["from a file", "atlas only"] and tables["regions"] == [{"id": "MBA:1", "name": "from a file"}]


def test_regions_and_modules_reach_the_snapshot(valid_tree, tmp_path, capsys):
    snapshot = tmp_path / "snapshot.json"
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--snapshot", str(snapshot)],
                atlas_loader=fake_loader(), terms_loader=terms_loader, connectivity_loader=no_claims) == 0
    assert "amygdala: 1 regions; prefrontal: 1 regions" in capsys.readouterr().out
    tables = json.loads(snapshot.read_text(encoding="utf-8"))["tables"]
    regions = {row["id"]: row["modules"] for row in tables["regions"]}
    assert regions["MBA:972"] == ["prefrontal"] and regions["MBA:44"] is None  # MBA:295's row comes from its file
    assert [(m["id"], m["position"]) for m in tables["modules"]] == [("amygdala", 1), ("prefrontal", 2)]
    prefrontal = tables["modules"][1]
    assert prefrontal["include"] == ["MBA:972", "UBERON:0004167"] and prefrontal["exclude"] == ["MBA:44"]
    assert prefrontal["terms"] == ["UBERON:0000451", "UBERON:0004167"]  # the root and the listed term; PL maps to none here
    assert prefrontal["labels"] == {"UBERON:0000451": "prefrontal cortex"}  # UBERON's, for terms under the root
    dumped = (tmp_path / "dist" / "modules.csv").read_text(encoding="utf-8")
    assert dumped.startswith("id,name,position,") and "prefrontal" in dumped
    assert json.loads((tmp_path / "dist" / "modules.json").read_text(encoding="utf-8"))["modules"][0]["id"] == "amygdala"


def test_a_module_without_regions_stops_build(valid_tree, tmp_path, capsys):
    (valid_tree / "modules.yaml").write_text(
        "modules:\n  - id: amygdala\n    name: Amygdala\n    roots: [UBERON:0001876]\n"
        "  - id: thalamus\n    name: Thalamus\n    include: [MBA:549]\n", encoding="utf-8")
    loader = fake_loader()
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=lambda atlas, terms: loader(atlas, TERMS),
                terms_loader=lambda roots: {"UBERON:0001876": AMYGDALA}, connectivity_loader=no_claims) == 1
    printed = capsys.readouterr().out
    assert "thalamus names MBA:549, which no loaded atlas has" in printed
    assert "allen-mouse-ccf-2017: no thalamus regions" in printed
