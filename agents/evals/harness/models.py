"""What an extractor returns: draft connectivity claims, in the schema's own terms.

The enumerations come from schema/axonarium.yaml, so a schema change reaches the harness without a code change.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

SCHEMA = Path(__file__).resolve().parents[3] / "schema" / "axonarium.yaml"
_ENUMS = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))["enums"]


def values(enum: str) -> tuple[str, ...]:
    """An enumeration's permissible values, in the schema's order."""
    return tuple(_ENUMS[enum]["permissible_values"])


EntityType = Literal[values("EntityType")]  # type: ignore[valid-type]
Predicate = Literal[values("ConnectivityPredicate")]  # type: ignore[valid-type]
EvidenceClass = Literal[values("EvidenceClass")]  # type: ignore[valid-type]
Result = Literal[values("Result")]  # type: ignore[valid-type]
Sign = Literal[values("Sign")]  # type: ignore[valid-type]


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: EntityType
    id: str = Field(description="An atlas region (MBA:, DHBA:), a UBERON term, a project neuron type (nt-) or a Cell Ontology term")
    name_in_paper: str = Field(description="The name the paper uses, as written")


class DraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: Entity
    predicate: Predicate
    object: Entity
    species: str = Field(description="NCBI Taxonomy ID, such as NCBITaxon:10090 for mouse or NCBITaxon:10116 for rat")
    evidence_class: EvidenceClass
    result: Result
    sign: Sign
    locator: str = Field(description="Where in the paper the evidence is, such as Fig. 3B")
    paraphrase: str = Field(description="The evidence in your own words; never copied text")


class Extraction(BaseModel):
    """Every connectivity claim a paper makes."""

    model_config = ConfigDict(extra="forbid")
    claims: list[DraftClaim]


class GoldEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: EntityType
    id: str


class GoldClaim(BaseModel):
    """A gold claim: the fields an extraction is scored on, plus where the curator found it."""

    model_config = ConfigDict(extra="forbid")
    subject: GoldEntity
    predicate: Predicate
    object: GoldEntity
    species: str
    evidence_class: EvidenceClass
    result: Result
    sign: Sign
    locator: str
