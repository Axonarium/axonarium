"""The serving tables (ADR 0008) as SQLAlchemy tables, and the rows the data files give them.

These definitions are the only description of the database schema: Alembic generates the migrations in
build/migrations from them, and CI's `alembic check` fails if the two ever differ.
"""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, MetaData, Table, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from build.edges import compute_edges
from build.terms import terms_of
from checks.findings import Record
from checks.identifiers import citation_of, source_key

metadata = MetaData()


def _text(name: str, required: bool = False) -> Column:
    return Column(name, Text, nullable=not required)


def _side(prefix: str) -> list[Column]:
    return [_text(f"{prefix}_type", True), _text(f"{prefix}_id", True), _text(f"{prefix}_atlas")]


def _citation_columns() -> list[Column]:
    return [Column("source_key", Text, ForeignKey("sources.id"), nullable=False), _text("doi"), _text("pmid"),
            _text("pmcid"), _text("arxiv"), _text("locator", True), _text("paraphrase", True), _text("excerpt"),
            Column("curation", JSONB, nullable=False), Column("verification", JSONB), _text("status", True),
            Column("extra", JSONB), _text("terms", True)]  # reuse terms, set by the build (build/terms.py)


atlases = Table(
    "atlases", metadata,
    Column("id", Text, primary_key=True), _text("name", True), _text("species", True), _text("version", True),
    _text("url"), _text("brainglobe_name"), _text("citation"), Column("extra", JSONB),
)
regions = Table(
    "regions", metadata,
    Column("id", Text, primary_key=True), _text("name", True), _text("acronym"),
    Column("atlas", Text, ForeignKey("atlases.id"), nullable=False), _text("parent"), _text("uberon"),
    Column("synonyms", ARRAY(Text)), Column("extra", JSONB),
    # Set by the build for atlas regions (ADR 0009): whether UBERON places the region's term under the amygdala,
    # and that term's label.
    Column("amygdala", Boolean), _text("uberon_label"),
)
neuron_types = Table(
    "neuron_types", metadata,
    Column("id", Text, primary_key=True), _text("name", True), _text("species", True), *_side("region"),
    _text("transmitter"), Column("markers", ARRAY(Text)), _text("cell_ontology"), Column("synonyms", ARRAY(Text)),
    Column("extra", JSONB),
)
sources = Table(
    "sources", metadata,
    Column("id", Text, primary_key=True), _text("title"), Column("year", Integer), _text("journal"), _text("kind", True),
    _text("license"), Column("open_access", Boolean), Column("retracted", Boolean), Column("extra", JSONB),
)
connectivity_claims = Table(
    "connectivity_claims", metadata,
    Column("id", Text, primary_key=True), *_side("subject"), _text("predicate", True), *_side("object"),
    _text("species", True), _text("evidence_class", True), _text("result", True), _text("sign", True),
    _text("strength"), Column("measurements", JSONB), *_citation_columns(),
)
homology_claims = Table(
    "homology_claims", metadata,
    Column("id", Text, primary_key=True), *_side("subject"), _text("subject_species", True), *_side("object"),
    _text("object_species", True), _text("correspondence", True), _text("confidence", True),
    Column("basis", ARRAY(Text), nullable=False), *_citation_columns(),
)
edges = Table(
    "edges", metadata,
    Column("id", Text, primary_key=True), _text("subject_id", True), _text("subject_type", True),
    _text("predicate", True), _text("object_id", True), _text("object_type", True), _text("species", True),
    *[Column(n, Integer, nullable=False) for n in ("n_claims", "n_present", "n_absent", "n_ambiguous", "n_disputed")],
    Column("evidence_classes", ARRAY(Text), nullable=False), _text("strength"),
    Column("signs", ARRAY(Text), nullable=False), Column("claim_ids", ARRAY(Text), nullable=False),
    Column("density", Float), Column("terms", ARRAY(Text), nullable=False),
)
retractions = Table(
    "retractions", metadata,
    Column("position", Integer, primary_key=True, autoincrement=False), _text("claim", True), _text("action", True),
    _text("reason", True), Column("curation", JSONB, nullable=False),
)

# The community inbox (sprint C.1, ADR 0021): evidence visitors submit for or against a claim. Operational state, not
# knowledge: written only by the site's server after its checks, read and closed only by triage, never loaded,
# emptied or dumped by the build, and closed to Supabase's public API roles.
submissions = Table(
    "submissions", metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    _text("claim", True), _text("stance", True), _text("identifier", True),  # identifier: as submitted
    Column("submitted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("status", Text, nullable=False, server_default="received"),
    _text("source_id"), _text("reason"),  # set by triage: the canonical source ID, and why it was closed
    Column("closed_at", DateTime(timezone=True)),
    CheckConstraint(r"claim ~ '^(clm|hom)-[0-9a-hjkmnp-tv-z]{10}$'", name="submissions_claim"),
    CheckConstraint("stance in ('supports', 'contradicts')", name="submissions_stance"),
    CheckConstraint("char_length(identifier) between 1 and 300", name="submissions_identifier"),
    CheckConstraint("status in ('received', 'closed')", name="submissions_status"),
)
OPERATIONAL = {"submissions"}  # tables the build never touches

# Every serving table by name, referenced tables first (the order dumps and loads use).
TABLES: dict[str, Table] = {table.name: table for table in metadata.sorted_tables if table.name not in OPERATIONAL}

CLASS_TABLES = {"Atlas": "atlases", "Region": "regions", "NeuronType": "neuron_types", "Source": "sources",
                "ConnectivityClaim": "connectivity_claims", "HomologyClaim": "homology_claims"}

# Nested parts of a record that are flattened into columns, and the keys each may hold.
FLATTENED = {
    "connectivity_claims": {"subject": {"type", "id", "atlas"}, "object": {"type", "id", "atlas"},
                            "source": {"doi", "pmid", "pmcid", "arxiv", "locator"}},
    "homology_claims": {"subject": {"type", "id", "atlas"}, "object": {"type", "id", "atlas"},
                        "source": {"doi", "pmid", "pmcid", "arxiv", "locator"}},
    "neuron_types": {"region": {"type", "id", "atlas"}},
}


def columns(table: str) -> list[str]:
    return [column.name for column in TABLES[table].columns]


def _check_fields(table: str, data: dict) -> None:
    """Every field of a record must land in a column: a schema change needs build/tables.py and a migration too."""
    known, flattened = set(columns(table)), FLATTENED.get(table, {})
    for key, value in data.items():
        if key in flattened:
            for inner in sorted(set(value) - flattened[key]):
                raise ValueError(f"{table}: {key}.{inner} has no column; add it to build/tables.py and a migration")
        elif key not in known:
            raise ValueError(f"{table}: {key} has no column; add it to build/tables.py and a migration")


def _flat_side(ref: dict, prefix: str) -> dict:
    return {f"{prefix}_type": ref["type"], f"{prefix}_id": ref["id"], f"{prefix}_atlas": ref.get("atlas")}


def _flat_citation(data: dict) -> dict:
    cited = citation_of(data)
    return {"source_key": source_key(cited), **{k: cited.get(k) for k in ("doi", "pmid", "pmcid", "arxiv", "locator")}}


def _row(table: str, data: dict) -> dict:
    """A row with every column of the table; values not in the record are None."""
    _check_fields(table, data)
    if table == "neuron_types":
        data = {**data, **_flat_side(data["region"], "region")}
    elif table in ("connectivity_claims", "homology_claims"):
        data = {**data, **_flat_side(data["subject"], "subject"), **_flat_side(data["object"], "object"),
                **_flat_citation(data), "terms": terms_of(data)}
    return {column: data.get(column) for column in columns(table)}


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
        key = TABLES[name].primary_key.columns.values()[0].name
        table.sort(key=lambda row: row[key])
    return tables
