"""The extractor's region lexicon (sprint 2.3, ADR 0028): every region of the pinned atlases that have region IDs,
with the UBERON term UBERON's bridges map it to, plus the project's neuron types.

Command line: `python -m ingest.lexicon --out .cache/lexicon.json [--http-cache .cache/build]`.

It is written at run time for the literature pipeline and never committed: Allen's region names carry the Allen
Institute's terms (ADR 0005). The pipeline gives it to the extractor, and drops any claim whose regions aren't in it.
"""

import argparse
import json
from pathlib import Path

from checks.loading import load_tree
from ingest.network import loaders

ROOT = Path(__file__).resolve().parents[1]


def lexicon(records, amygdala_loader, atlas_loader) -> dict:
    """{"atlases": {atlas id: {species, regions: [{id, acronym, name, uberon}]}}, "neuron_types": [{id, name, ...}]}"""
    terms = amygdala_loader()
    atlases = {}
    for record in records:
        if record.cls != "Atlas" or not record.data.get("brainglobe_name"):
            continue
        rows = atlas_loader(record.data, terms)
        if rows:
            atlases[record.data["id"]] = {
                "species": record.data["species"],
                "regions": [{"id": r["id"], "acronym": r["acronym"], "name": r["name"], "uberon": r["uberon"],
                             "amygdala": r["amygdala"]} for r in rows],
            }
    neuron_types = sorted(({"id": r.data["id"], "name": r.data["name"], "species": r.data["species"],
                            "region": r.data["region"]["id"]} for r in records if r.cls == "NeuronType"),
                          key=lambda n: n["id"])
    return {"atlases": atlases, "neuron_types": neuron_types}


def main(argv: list[str] | None = None, network=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest.lexicon", description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True, help="where to write the lexicon (JSON); not in the repository's data")
    parser.add_argument("--data", type=Path, default=ROOT / "data", help="the data folder (default data)")
    parser.add_argument("--http-cache", type=Path, help="cache HTTP answers here for seven days, as the build does")
    args = parser.parse_args(argv)
    records, _ = load_tree(args.data)
    amygdala_loader, atlas_loader, _ = network or loaders(args.http_cache)
    found = lexicon(records, amygdala_loader, atlas_loader)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(found, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = ", ".join(f"{atlas}: {len(entry['regions'])} regions" for atlas, entry in found["atlases"].items())
    print(f"lexicon: {counts}; {len(found['neuron_types'])} neuron types; written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
