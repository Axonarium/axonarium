"""Atlas regions in the build: merged into the database rows, checked against data, kept out of the dumps."""

import json

from build.cli import main
from checks.tests.conftest import overlay  # noqa: F401
from ingest.atlases import AtlasPinMismatch

# Every MBA region the valid tree's claims and neuron types name, so a fake atlas can hold them all.
USED = ["MBA:1105", "MBA:131", "MBA:194", "MBA:295", "MBA:382", "MBA:403", "MBA:44", "MBA:536", "MBA:551", "MBA:559",
        "MBA:56", "MBA:693", "MBA:703", "MBA:795", "MBA:867", "MBA:972"]


AMYGDALA = {"UBERON:0001876": "amygdala", "UBERON:0002887": "basal amygdaloid nucleus"}


def amygdala_loader():
    return AMYGDALA


def fake_loader(ids=USED, amygdala="MBA:295", empty=()):
    def load(atlas, terms):
        assert terms == AMYGDALA
        if atlas["id"] in empty:
            return []
        return [{"id": i, "name": f"Region {i}", "acronym": i.split(":")[1], "atlas": atlas["id"], "parent": None,
                 "uberon": "UBERON:0002887" if i == amygdala else None, "amygdala": i == amygdala,
                 "uberon_label": "basal amygdaloid nucleus" if i == amygdala else None, "synonyms": None, "extra": None}
                for i in ids]
    return load


def test_atlas_regions_reach_the_database_rows_not_the_dumps(valid_tree, tmp_path, capsys):
    out = tmp_path / "dist"
    assert main(["--data", str(valid_tree), "--out", str(out)], atlas_loader=fake_loader(), amygdala_loader=amygdala_loader) == 0
    printed = capsys.readouterr().out
    assert "allen-mouse-ccf-2017: 16 regions" in printed and "amygdala" in printed
    dumped = json.loads((out / "axonarium.json").read_text(encoding="utf-8"))
    assert not any(r["name"].startswith("Region MBA:") for r in dumped["regions"])  # atlas-derived names stay out (ADR 0005)
    assert "Region MBA:295" not in (out / "regions.csv").read_text(encoding="utf-8")


def test_unknown_region_stops_build(valid_tree, tmp_path, capsys):
    loader = fake_loader([i for i in USED if i != "MBA:559"])
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=loader, amygdala_loader=amygdala_loader) == 1
    printed = capsys.readouterr().out
    assert "unknown-region" in printed and "MBA:559" in printed and "allen-mouse-ccf-2017" in printed


def test_no_atlases_skips_loading(valid_tree, tmp_path):
    def refuse(*args):
        raise AssertionError("atlases must not load with --no-atlases")
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist"), "--no-atlases"], atlas_loader=refuse, amygdala_loader=refuse) == 0


def test_pin_mismatch_reported(valid_tree, tmp_path, capsys):
    def mismatched(atlas, terms):
        raise AtlasPinMismatch("allen-mouse-ccf-2017 pins 3.1, but BrainGlobe serves 3.2")
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=mismatched, amygdala_loader=amygdala_loader) == 1
    assert "BrainGlobe serves 3.2" in capsys.readouterr().out


def test_atlas_without_amygdala_stops_build(valid_tree, tmp_path, capsys):
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=fake_loader(amygdala=None), amygdala_loader=amygdala_loader) == 1
    assert "no amygdala regions" in capsys.readouterr().out


def test_region_ids_checked_in_atlases_without_regions(valid_tree, tmp_path, capsys):
    # The example atlas, loaded with no regions (like Waxholm), can't hold MBA:295 or any other region ID.
    loader = fake_loader(empty=("allen-mouse-ccf-2017",))
    assert main(["--data", str(valid_tree), "--out", str(tmp_path / "dist")], atlas_loader=loader, amygdala_loader=amygdala_loader) == 1
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
