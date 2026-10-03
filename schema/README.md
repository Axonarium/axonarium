# Schema

`axonarium.yaml` is the [LinkML](https://linkml.io/) schema for everything in `data/`. It is the one definition the JSON Schemas and SQL in `generated/` are produced from.

To validate a single record file in an editor or another tool, use the schema for its class, such as `generated/json/ConnectivityClaim.schema.json`, and turn on format checking so dates are checked. `generated/axonarium.schema.json` describes a whole-database dump (`KnowledgeBase`) and accepts any single record file without checking it. `generated/axonarium.sql` is a reference mapping of the classes to PostgreSQL tables, not the production layout (sprint 0.4 designs that). Version 0.2.0. Sprint 0.2 of [docs/plan.md](../docs/plan.md) created it ([design](../docs/specs/2026-10-02-sprint-0.2-schema.md), including what is out of scope); sprint 0.3 added the retractions log ([design](../docs/specs/2026-10-03-sprint-0.3-validation.md)).

## What it describes

| Class | One record is |
| --- | --- |
| `ConnectivityClaim` | A cited statement that a region or neuron type connects to another in one species. ID `clm-…` |
| `HomologyClaim` | A cited statement that an entity in one species corresponds to one in another. ID `hom-…` |
| `Atlas` | A pinned atlas version |
| `Region` | A structure in one atlas version, mapped to UBERON |
| `NeuronType` | A neuron population, mapped to the Cell Ontology where a term exists. ID `nt-…` |
| `Source` | Cached metadata for a paper or preprint |
| `RetractionLog` | The log of deleted and retracted claims, `data/retractions.yaml` |

Both claim classes share a citation, a paraphrase, an optional short excerpt, curation and verification records, a status, and the open-ended `extra` map.

## Rules it enforces

1. Each predicate allows only its own evidence classes:

   | Predicate | Evidence classes |
   | --- | --- |
   | `projects_to` | anterograde_tracer, retrograde_tracer, single_neuron_reconstruction |
   | `synapses_onto` | electron_microscopy, transsynaptic_tracer |
   | `functionally_connects_to` | optogenetic_circuit_mapping, paired_recording, electrical_stimulation |

2. A region is an MBA or HBA atlas ID, which must name its `atlas`, or a UBERON term. A neuron type is an `nt-` ID or a Cell Ontology term.
3. A human curator or verifier gives an ORCID. An agent gives its model and versioned prompt, such as `extract@1.0.0`.
4. A citation has at least one of `doi`, `pmid`, `pmcid` or `arxiv`, plus a locator such as "Fig. 3B".
5. IDs are a type prefix plus 10 random characters ([ADR 0004](../docs/decisions/0004-identifiers.md)).

Not enforced yet (sprint 0.3): the format of `extra` keys, references between files, ID uniqueness across `data/`, units matching their quantity, and a homology claim's two species being different.

## Examples

`examples/valid/` holds 20 illustrative claims and the entities they reference. `examples/invalid/` holds claims that each break one rule, with the expected error on the first line. File names start with the class, as in `ConnectivityClaim-bla-to-ceam.yaml`.

The examples are not evidence. Every citation uses Crossref's test DOI prefix `10.5555`, and every paraphrase says it is illustrative. Real claims start with the gold set (sprint 0.5).

## Commands

Validate one file:

```bash
uv run linkml-validate -s schema/axonarium.yaml -C ConnectivityClaim path/to/file.yaml
```

Run the tests, which pre-commit and CI also run:

```bash
uv run pytest schema/tests
```

Regenerate after changing the schema; a test fails until you do:

```bash
uv run gen-json-schema schema/axonarium.yaml > schema/generated/axonarium.schema.json
for c in ConnectivityClaim HomologyClaim Atlas Region NeuronType Source RetractionLog; do
  uv run gen-json-schema --top-class $c --closed schema/axonarium.yaml > schema/generated/json/$c.schema.json
done
uv run gen-sqltables --dialect postgresql --autogenerate_index false --generate_abstract_class_ddl false schema/axonarium.yaml > schema/generated/axonarium.sql
```

## Writing YAML for this schema

- Quote dates and PMIDs (`"2026-10-02"`, `"12345678"`). Unquoted, YAML turns them into dates and numbers.
- Region IDs are limited to MBA, HBA and UBERON until sprint 1.2 pins the rat and human atlases.
- Namespace `extra` keys: `lab.tracer`, not `tracer`.
