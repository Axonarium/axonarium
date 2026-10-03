"""The serving tables (ADR 0008): their columns, and the rows the data files give them."""

from build.edges import compute_edges
from checks.findings import Record
from checks.identifiers import citation_of, source_key

CITATION = [("source_key", "text not null references sources (id)"), ("doi", "text"), ("pmid", "text"), ("pmcid", "text"),
            ("arxiv", "text"), ("locator", "text not null"), ("paraphrase", "text not null"), ("excerpt", "text"),
            ("curation", "jsonb not null"), ("verification", "jsonb"), ("status", "text not null"), ("extra", "jsonb")]

# Table name -> (column, SQL type), in creation order: referenced tables first. The first column is the key.
TABLES: dict[str, list[tuple[str, str]]] = {
    "atlases": [("id", "text primary key"), ("name", "text not null"), ("species", "text not null"),
                ("version", "text not null"), ("url", "text"), ("brainglobe_name", "text"), ("extra", "jsonb")],
    "regions": [("id", "text primary key"), ("name", "text not null"), ("acronym", "text"),
                ("atlas", "text not null references atlases (id)"), ("parent", "text"), ("uberon", "text"),
                ("synonyms", "text[]"), ("extra", "jsonb")],
    "neuron_types": [("id", "text primary key"), ("name", "text not null"), ("species", "text not null"),
                     ("region_type", "text not null"), ("region_id", "text not null"), ("region_atlas", "text"),
                     ("transmitter", "text"), ("markers", "text[]"), ("cell_ontology", "text"), ("synonyms", "text[]"),
                     ("extra", "jsonb")],
    "sources": [("id", "text primary key"), ("title", "text"), ("year", "integer"), ("journal", "text"),
                ("license", "text"), ("open_access", "boolean"), ("retracted", "boolean"), ("extra", "jsonb")],
    "connectivity_claims": [("id", "text primary key"), ("subject_type", "text not null"), ("subject_id", "text not null"),
                            ("subject_atlas", "text"), ("predicate", "text not null"), ("object_type", "text not null"),
                            ("object_id", "text not null"), ("object_atlas", "text"), ("species", "text not null"),
                            ("evidence_class", "text not null"), ("result", "text not null"), ("sign", "text not null"),
                            ("strength", "text"), ("measurements", "jsonb"), *CITATION],
    "homology_claims": [("id", "text primary key"), ("subject_type", "text not null"), ("subject_id", "text not null"),
                        ("subject_atlas", "text"), ("subject_species", "text not null"), ("object_type", "text not null"),
                        ("object_id", "text not null"), ("object_atlas", "text"), ("object_species", "text not null"),
                        ("correspondence", "text not null"), ("confidence", "text not null"), ("basis", "text[] not null"),
                        *CITATION],
    "edges": [("id", "text primary key"), ("subject_id", "text not null"), ("subject_type", "text not null"),
              ("predicate", "text not null"), ("object_id", "text not null"), ("object_type", "text not null"),
              ("species", "text not null"), ("n_claims", "integer not null"), ("n_present", "integer not null"),
              ("n_absent", "integer not null"), ("n_ambiguous", "integer not null"), ("n_disputed", "integer not null"),
              ("evidence_classes", "text[] not null"), ("strength", "text"), ("signs", "text[] not null"),
              ("claim_ids", "text[] not null")],
    "retractions": [("position", "integer primary key"), ("claim", "text not null"), ("action", "text not null"),
                    ("reason", "text not null"), ("curation", "jsonb not null")],
}


def _side(ref: dict, prefix: str) -> dict:
    return {f"{prefix}_type": ref["type"], f"{prefix}_id": ref["id"], f"{prefix}_atlas": ref.get("atlas")}


def _citation(data: dict) -> dict:
    cited = citation_of(data)
    return {"source_key": source_key(cited), **{k: cited.get(k) for k in ("doi", "pmid", "pmcid", "arxiv", "locator")}}


def _row(table: str, data: dict) -> dict:
    """A row with every column of the table; values not in the record are None."""
    if table == "neuron_types":
        region = data["region"]
        data = {**data, "region_type": region["type"], "region_id": region["id"], "region_atlas": region.get("atlas")}
    elif table == "connectivity_claims":
        data = {**data, **_side(data["subject"], "subject"), **_side(data["object"], "object"), **_citation(data)}
    elif table == "homology_claims":
        data = {**data, **_side(data["subject"], "subject"), **_side(data["object"], "object"), **_citation(data)}
    return {column: data.get(column) for column, _ in TABLES[table]}


CLASS_TABLES = {"Atlas": "atlases", "Region": "regions", "NeuronType": "neuron_types", "Source": "sources",
                "ConnectivityClaim": "connectivity_claims", "HomologyClaim": "homology_claims"}


def rows(records: list[Record]) -> dict[str, list[dict]]:
    """Every table's rows from validated records, each table sorted by its key."""
    tables: dict[str, list[dict]] = {name: [] for name in TABLES}
    for record in records:
        if record.cls in CLASS_TABLES:
            tables[CLASS_TABLES[record.cls]].append(_row(CLASS_TABLES[record.cls], record.data))
        elif record.cls == "RetractionLog":
            tables["retractions"] = [_row("retractions", {**entry, "position": i})
                                     for i, entry in enumerate(record.data["entries"], start=1)]
    tables["edges"] = compute_edges(records)
    for name, table in tables.items():
        table.sort(key=lambda row: row[TABLES[name][0][0]])
    return tables
