"""Module membership (ADR 0031): UBERON roots, included and excluded regions and terms, subdivisions with their parent."""

from pathlib import Path

import yaml

from ingest.modules import apply, labels, resolve, roots_of, structures

MODULES = yaml.safe_load((Path(__file__).resolve().parents[2] / "data" / "modules.yaml").read_text(encoding="utf-8"))["modules"]


def row(number: int, uberon: str | None = None, parent: int | None = None, atlas: str = "allen-mouse-ccf-2017") -> dict:
    return {"id": f"MBA:{number}", "atlas": atlas, "parent": f"MBA:{parent}" if parent else None, "uberon": uberon}


# A small Allen-like tree. The amygdala: BLA with an unmapped subdivision BLAa. The hippocampal formation: HPF with CA1,
# the retrohippocampal region (RHP) and its entorhinal area (ENT, mapped to a term no root holds), and the fornix
# system, a fibre tract UBERON puts under it. The prefrontal cortex: PL and ILA (under its root), and ACA, ORB and FRP
# (listed). CP belongs to none.
ROWS = [
    row(997),
    row(295, "UBERON:0002887", 997), row(303, None, 295),
    row(1089, "UBERON:0002421", 997), row(382, "UBERON:0003881", 1089), row(822, "UBERON:0022230", 1089),
    row(909, "UBERON:0002728", 822), row(1099, "UBERON:0000052", 997), row(603, "UBERON:0002310", 1099),
    row(972, "UBERON:8440032", 997), row(44, "UBERON:8440033", 997), row(31, "UBERON:0009835", 997),
    row(48, None, 31), row(714, None, 997), row(184, "UBERON:0002795", 997),
    row(672, "UBERON:0001873", 997),
]
TERMS = {
    "UBERON:0001876": {"UBERON:0001876": "amygdala", "UBERON:0002887": "basal amygdaloid nucleus"},
    "UBERON:0002421": {"UBERON:0002421": "hippocampal formation", "UBERON:0003881": "CA1 field of hippocampus",
                       "UBERON:0022230": "retrohippocampal region", "UBERON:0000052": "fornix of brain",
                       "UBERON:0002310": "hippocampus fimbria"},
    "UBERON:0000451": {"UBERON:0000451": "prefrontal cortex", "UBERON:8440032": "prelimbic area",
                       "UBERON:8440033": "infralimbic area"},
}


def test_the_projects_modules_resolve():
    members, terms = resolve(MODULES, ROWS, TERMS)
    by_module = {m["id"]: sorted(r for r, found in members.items() if m["id"] in found) for m in MODULES}
    assert by_module == {
        "amygdala": ["MBA:295", "MBA:303"],  # BLAa, with no UBERON term, follows BLA
        "hippocampus": ["MBA:1089", "MBA:382", "MBA:822", "MBA:909"],  # ENT through RHP; the fornix system left out
        "prefrontal": ["MBA:184", "MBA:31", "MBA:44", "MBA:48", "MBA:714", "MBA:972"],
    }
    assert "UBERON:0002728" in terms["hippocampus"]  # entorhinal cortex, as rat claims name it, through ENT
    assert not {"UBERON:0000052", "UBERON:0002310"} & set(terms["hippocampus"])
    assert {"UBERON:0004167", "UBERON:0009835", "UBERON:8440032"} <= set(terms["prefrontal"])  # listed, mapped, rooted


def test_a_region_in_two_modules_lists_both_in_order():
    modules = [{"id": "a", "name": "A", "roots": ["UBERON:0002887"]}, {"id": "b", "name": "B", "include": ["MBA:303"]}]
    members, _ = resolve(modules, ROWS, {"UBERON:0002887": {"UBERON:0002887": ""}})
    assert members["MBA:303"] == ["a", "b"] and members["MBA:295"] == ["a"]


def test_an_excluded_term_takes_its_regions_and_their_subdivisions():
    modules = [{"id": "p", "name": "P", "include": ["MBA:31", "MBA:972"], "exclude": ["UBERON:0009835"]}]
    members, terms = resolve(modules, ROWS, {})
    assert sorted(members) == ["MBA:972"] and terms["p"] == ["UBERON:8440032"]


def test_apply_sets_each_rows_modules_and_structures_reads_them():
    loaded = {"allen-mouse-ccf-2017": [dict(r) for r in ROWS]}
    apply(MODULES, loaded, TERMS)
    rows = loaded["allen-mouse-ccf-2017"]
    assert next(r for r in rows if r["id"] == "MBA:672")["modules"] is None
    assert structures(rows, "amygdala") == [295, 303]
    assert structures(rows) == sorted([295, 303, 1089, 382, 822, 909, 972, 44, 31, 48, 714, 184])


def test_labels_name_the_terms_under_a_root():
    _, terms = resolve(MODULES, ROWS, TERMS)
    found = labels(terms, TERMS)
    assert found["hippocampus"]["UBERON:0003881"] == "CA1 field of hippocampus"
    assert "UBERON:0002728" not in found["hippocampus"]  # entorhinal cortex comes through ENT, not from OLS here
    assert "UBERON:0004167" not in found["prefrontal"]  # listed, not under the root


def test_roots_once_each_in_order():
    assert roots_of(MODULES) == ["UBERON:0001876", "UBERON:0002421", "UBERON:0000451"]
    assert roots_of([*MODULES, {"id": "x", "name": "X", "roots": ["UBERON:0001876"]}]) == roots_of(MODULES)
