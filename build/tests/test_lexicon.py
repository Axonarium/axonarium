"""The extractor's region lexicon (sprint 2.3): the pinned atlases' regions and the project's neuron types."""

import json

from ingest.lexicon import main
from build.tests.test_regions import USED, amygdala_loader, fake_loader


def test_lexicon_lists_each_atlas_with_region_ids_and_the_neuron_types(valid_tree, tmp_path, capsys):
    out = tmp_path / "cache" / "lexicon.json"
    assert main(["--data", str(valid_tree), "--out", str(out)], network=(amygdala_loader, fake_loader(), None)) == 0
    found = json.loads(out.read_text(encoding="utf-8"))
    mouse = found["atlases"]["allen-mouse-ccf-2017"]
    assert mouse["species"] == "NCBITaxon:10090" and len(mouse["regions"]) == len(USED)
    bla = next(r for r in mouse["regions"] if r["id"] == "MBA:295")
    assert bla == {"id": "MBA:295", "acronym": "295", "name": "Region MBA:295", "uberon": "UBERON:0002887", "amygdala": True}
    assert found["neuron_types"] and all(n["id"].startswith("nt-") and n["region"] for n in found["neuron_types"])
    assert "lexicon: allen-mouse-ccf-2017:" in capsys.readouterr().out
