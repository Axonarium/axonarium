"""Atlas regions at build time: hierarchies from BrainGlobe, mapped to UBERON by UBERON's own bridges (ADR 0009).

Nothing here is committed: Allen content stays out of the repository (ADR 0005), and each run reads the
pinned atlas version from BrainGlobe.
"""

from collections.abc import Callable

import rdflib
import requests

# BrainGlobe atlas name (metadata "name") -> the prefix of its region IDs. Atlases not listed give no regions.
PREFIXES = {"allen_mouse": "MBA", "allen_human": "DHBA"}
BASES = {"MBA": "https://purl.brain-bican.org/ontology/mbao/MBA_",
         "DHBA": "https://purl.brain-bican.org/ontology/dhbao/DHBA_"}
BRIDGES = {"MBA": "http://purl.obolibrary.org/obo/uberon/bridge/uberon-bridge-to-mba.owl",
           "DHBA": "http://purl.obolibrary.org/obo/uberon/bridge/uberon-bridge-to-dhba.owl"}
UBERON = "http://purl.obolibrary.org/obo/UBERON_"
# The amygdala and the nuclei claims name (UBERON), used to show and check what each atlas resolves.
AMYGDALA = {
    "UBERON:0001876",  # amygdala
    "UBERON:0006107",  # basolateral amygdaloid nuclear complex
    "UBERON:0002886",  # lateral amygdaloid nucleus
    "UBERON:0002887",  # basal amygdaloid nucleus
    "UBERON:0002885",  # accessory basal amygdaloid nucleus
    "UBERON:0002883",  # central amygdaloid nucleus
    "UBERON:0002892",  # medial amygdaloid nucleus
    "UBERON:0006108",  # corticomedial nuclear complex
    "UBERON:0002890",  # anterior amygdaloid area
    "UBERON:0002884",  # intercalated amygdaloid nuclei
}
# A region maps exactly when its equivalent class is a UBERON class restricted to the species.
BRIDGE_QUERY = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?region ?uberon WHERE {
  ?region owl:equivalentClass/owl:intersectionOf/rdf:first ?uberon .
  FILTER(STRSTARTS(STR(?uberon), "http://purl.obolibrary.org/obo/UBERON_"))
}
"""


class AtlasPinMismatch(Exception):
    """BrainGlobe serves a different atlas version than the atlas record pins, or the record pins none."""


def bridge_mappings(owl: str, prefix: str) -> dict[str, str]:
    """Atlas region ID -> UBERON term, from a UBERON bridge in OWL (RDF/XML)."""
    graph = rdflib.Graph()
    graph.parse(data=owl, format="xml")
    mappings: dict[str, str] = {}
    for region, uberon in sorted(graph.query(BRIDGE_QUERY)):
        region, uberon = str(region), str(uberon)
        if region.startswith(BASES[prefix]):
            mappings.setdefault(f"{prefix}:{region.removeprefix(BASES[prefix])}", f"UBERON:{uberon.removeprefix(UBERON)}")
    return mappings


def region_rows(atlas_id: str, structures: list[dict], prefix: str, mappings: dict[str, str]) -> list[dict]:
    """One `regions` row per atlas structure, sorted by ID."""
    rows = []
    for structure in structures:
        region = f"{prefix}:{structure['id']}"
        parent = structure.get("parent_structure_id")
        rows.append({"id": region, "name": structure["name"], "acronym": structure["acronym"], "atlas": atlas_id,
                     "parent": f"{prefix}:{parent}" if parent is not None else None,
                     "uberon": mappings.get(region), "synonyms": None, "extra": None})
    return sorted(rows, key=lambda row: row["id"])


def _open_brainglobe(name: str):
    from brainglobe_atlasapi import BrainGlobeAtlas  # Imported here: it is heavy, and only real builds need it.

    return BrainGlobeAtlas(name, check_latest=False)


def _download(url: str) -> str:
    response = requests.get(url, timeout=120, headers={"User-Agent": "axonarium-build (https://github.com/axonarium/axonarium)"})
    response.raise_for_status()
    return response.text


def load_atlas(atlas: dict, open_atlas: Callable = _open_brainglobe, fetch: Callable[[str], str] = _download) -> list[dict]:
    """The region rows of one atlas record, from its pinned BrainGlobe atlas; [] if the atlas has no region IDs."""
    pinned = (atlas.get("extra") or {}).get("brainglobe.atlas_version")
    if pinned is None:
        raise AtlasPinMismatch(f"{atlas['id']} names a BrainGlobe atlas but pins no brainglobe.atlas_version in extra")
    brainglobe = open_atlas(atlas["brainglobe_name"])
    served = str(brainglobe.metadata["version"])
    if served != str(pinned):
        raise AtlasPinMismatch(f"{atlas['id']} pins BrainGlobe {atlas['brainglobe_name']} {pinned}, but BrainGlobe "
                               f"serves {served}; review the new version and update the pin")
    prefix = PREFIXES.get(brainglobe.metadata["name"])
    if prefix is None:
        return []
    mappings = bridge_mappings(fetch(BRIDGES[prefix]), prefix)
    return region_rows(atlas["id"], list(brainglobe.structures.values()), prefix, mappings)
