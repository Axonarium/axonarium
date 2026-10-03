"""Atlas regions at build time: hierarchies from BrainGlobe, mapped to UBERON by UBERON's own bridges (ADR 0009).

Nothing here is committed: Allen content stays out of the repository (ADR 0005). Each build reads the pinned
atlas version from BrainGlobe and the pinned UBERON release's bridges.
"""

import hashlib
from collections.abc import Callable
from urllib.parse import quote

import rdflib
import requests

# BrainGlobe atlas name (metadata "name") -> the prefix of its region IDs. Atlases not listed give no regions.
PREFIXES = {"allen_mouse": "MBA", "allen_human": "DHBA"}
BASES = {"MBA": "https://purl.brain-bican.org/ontology/mbao/MBA_",
         "DHBA": "https://purl.brain-bican.org/ontology/dhbao/DHBA_"}
# UBERON's bridges, pinned to a release tag and a checksum: a new release is a reviewed change, like an atlas pin.
UBERON_RELEASE = "v2026-10-01"
_BRIDGE_URL = "https://raw.githubusercontent.com/obophenotype/uberon/{release}/src/ontology/bridge/uberon-bridge-to-{name}.owl"
BRIDGES = {
    "MBA": (_BRIDGE_URL.format(release=UBERON_RELEASE, name="mba"),
            "2d712f5aff254606ca4585828dddb0d61e7e0364d517829a5562423808e04775"),
    "DHBA": (_BRIDGE_URL.format(release=UBERON_RELEASE, name="dhba"),
             "3f904b474c54c4b799b45b6b50763bdf61e8b51e2af6fa59d690ae567a53ff9f"),
}
UBERON = "http://purl.obolibrary.org/obo/UBERON_"
AMYGDALA_ROOT = ("UBERON:0001876", "amygdala")
OLS_DESCENDANTS = ("https://www.ebi.ac.uk/ols4/api/ontologies/uberon/terms/{iri}/hierarchicalDescendants"
                   "?size=500&page={page}")
# A region maps exactly when its equivalent class is a UBERON class restricted to a species, and nothing else.
BRIDGE_QUERY = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?region ?uberon WHERE {
  ?region owl:equivalentClass/owl:intersectionOf ?list .
  ?list rdf:first ?uberon ; rdf:rest ?rest .
  ?rest rdf:first ?restriction ; rdf:rest rdf:nil .
  ?restriction owl:someValuesFrom ?taxon .
  FILTER(STRSTARTS(STR(?uberon), "http://purl.obolibrary.org/obo/UBERON_"))
  FILTER(STRSTARTS(STR(?taxon), "http://purl.obolibrary.org/obo/NCBITaxon_"))
}
"""
USER_AGENT = {"User-Agent": "axonarium-build (https://github.com/axonarium/axonarium)"}


class AtlasPinMismatch(Exception):
    """BrainGlobe serves a different atlas version than the atlas record pins, or the record pins none."""


class BridgeMismatch(Exception):
    """A UBERON bridge doesn't match its pinned checksum."""


def bridge_mappings(owl: str | bytes, prefix: str) -> dict[str, str]:
    """Atlas region ID -> UBERON term, from a UBERON bridge in OWL (RDF/XML)."""
    graph = rdflib.Graph()
    graph.parse(data=owl, format="xml")
    mappings: dict[str, str] = {}
    for region, uberon in sorted(graph.query(BRIDGE_QUERY)):
        region, uberon = str(region), str(uberon)
        if region.startswith(BASES[prefix]):
            mappings.setdefault(f"{prefix}:{region.removeprefix(BASES[prefix])}", f"UBERON:{uberon.removeprefix(UBERON)}")
    return mappings


def _get_json(url: str) -> dict:
    response = requests.get(url, timeout=60, headers={**USER_AGENT, "Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def amygdala_terms(fetch_json: Callable[[str], dict] = _get_json) -> dict[str, str]:
    """The amygdala and every UBERON term under it (is-a or part-of, as OLS computes it), with labels."""
    iri = quote(quote(UBERON + AMYGDALA_ROOT[0].split(":")[1], safe=""), safe="")
    terms, page = {AMYGDALA_ROOT[0]: AMYGDALA_ROOT[1]}, 0
    while True:
        answer = fetch_json(OLS_DESCENDANTS.format(iri=iri, page=page))
        for term in answer.get("_embedded", {}).get("terms", []):
            if str(term.get("obo_id", "")).startswith("UBERON:"):
                terms[term["obo_id"]] = term["label"]
        page += 1
        if page >= answer.get("page", {}).get("totalPages", 1):
            return terms


def region_rows(atlas_id: str, structures: list[dict], prefix: str, mappings: dict[str, str],
                amygdala: dict[str, str]) -> list[dict]:
    """One `regions` row per atlas structure, sorted by ID; every parent must be a region of the same atlas."""
    ids = {f"{prefix}:{s['id']}" for s in structures}
    rows = []
    for structure in structures:
        region = f"{prefix}:{structure['id']}"
        path = structure["structure_id_path"]  # BrainGlobe 3.0.2 wraps parent IDs above 65535; the path doesn't.
        parent = f"{prefix}:{path[-2]}" if len(path) > 1 else None
        if parent is not None and parent not in ids:
            raise ValueError(f"{atlas_id}: {region}'s parent {parent} is not a region of the atlas")
        uberon = mappings.get(region)
        rows.append({"id": region, "name": structure["name"], "acronym": structure["acronym"], "atlas": atlas_id,
                     "parent": parent, "uberon": uberon, "amygdala": uberon in amygdala,
                     "uberon_label": amygdala.get(uberon), "synonyms": None, "extra": None})
    return sorted(rows, key=lambda row: row["id"])


def _open_brainglobe(name: str, version: str):
    from brainglobe_atlasapi import BrainGlobeAtlas  # Imported here: it is heavy, and only real builds need it.

    return BrainGlobeAtlas(name, version=version, check_latest=False)


def _download(url: str) -> bytes:
    response = requests.get(url, timeout=120, headers=USER_AGENT)
    response.raise_for_status()
    return response.content


def load_atlas(atlas: dict, amygdala: dict[str, str], open_atlas: Callable = _open_brainglobe,
               fetch: Callable[[str], str | bytes] = _download, bridges: dict = BRIDGES) -> list[dict]:
    """The region rows of one atlas record, from its pinned BrainGlobe atlas; [] if the atlas has no region IDs."""
    pinned = (atlas.get("extra") or {}).get("brainglobe.atlas_version")
    if pinned is None:
        raise AtlasPinMismatch(f"{atlas['id']} names a BrainGlobe atlas but pins no brainglobe.atlas_version in extra")
    brainglobe = open_atlas(atlas["brainglobe_name"], str(pinned))
    served = str(brainglobe.metadata["version"])
    if served != str(pinned):  # A safety net: BrainGlobe is asked for the pinned version.
        raise AtlasPinMismatch(f"{atlas['id']} pins BrainGlobe {atlas['brainglobe_name']} {pinned}, but BrainGlobe "
                               f"served {served}")
    prefix = PREFIXES.get(brainglobe.metadata["name"])
    if prefix is None:
        return []
    url, checksum = bridges[prefix]
    raw = fetch(url)
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    if hashlib.sha256(data).hexdigest() != checksum:
        raise BridgeMismatch(f"{url} doesn't match its pinned sha256; review the new bridge and update the pin")
    mappings = bridge_mappings(data, prefix)
    return region_rows(atlas["id"], list(brainglobe.structures.values()), prefix, mappings, amygdala)
