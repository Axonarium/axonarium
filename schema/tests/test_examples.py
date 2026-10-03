"""The schema accepts its valid examples and rejects each invalid one for the stated reason."""

from pathlib import Path

import pytest
import yaml
from linkml.validator import validate, validate_file

SCHEMA_DIR = Path(__file__).resolve().parent.parent
SCHEMA = str(SCHEMA_DIR / "axonarium.yaml")
VALID = sorted((SCHEMA_DIR / "examples" / "valid").glob("*.yaml"))
INVALID = sorted((SCHEMA_DIR / "examples" / "invalid").glob("*.yaml"))


def target_class(path: Path) -> str:
    """The class an example instantiates: its file name up to the first hyphen."""
    return Path(path).name.split("-", 1)[0]


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def errors(report) -> list[str]:
    return [r.message for r in report.results if getattr(r.severity, "name", r.severity) == "ERROR"]


def test_examples_exist():
    assert VALID, "no valid examples found"
    assert INVALID, "no invalid examples found"


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_examples_validate(path):
    assert errors(validate_file(str(path), SCHEMA, target_class(path))) == []


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_examples_fail_for_the_stated_reason(path):
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("# expect: "), f"{path.name} must start with '# expect: <text>'"
    expected = first_line.removeprefix("# expect: ")
    messages = errors(validate_file(str(path), SCHEMA, target_class(path)))
    assert any(expected in m for m in messages), messages


def test_example_ids_are_unique():
    ids = [load(p)["id"] for p in VALID]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_excerpt_limit():
    claim = load(SCHEMA_DIR / "examples" / "valid" / "ConnectivityClaim-bla-to-ceam.yaml")
    claim["excerpt"] = "x" * 300
    assert errors(validate(claim, SCHEMA, "ConnectivityClaim")) == []
    claim["excerpt"] = "x" * 301
    messages = errors(validate(claim, SCHEMA, "ConnectivityClaim"))
    assert any(m.endswith("in /excerpt") for m in messages), messages


def test_references_resolve_within_examples():
    by_class = {}
    for path in VALID:
        by_class.setdefault(target_class(path), []).append(load(path))
    refs = [ref for cls in ("ConnectivityClaim", "HomologyClaim") for claim in by_class.get(cls, [])
            for ref in (claim["subject"], claim["object"])]
    refs += [neuron_type["region"] for neuron_type in by_class.get("NeuronType", [])]
    neuron_types = {neuron_type["id"] for neuron_type in by_class.get("NeuronType", [])}
    atlases = {atlas["id"] for atlas in by_class.get("Atlas", [])}
    used_neuron_types = {ref["id"] for ref in refs if str(ref["id"]).startswith("nt-")}
    used_atlases = {ref["atlas"] for ref in refs if "atlas" in ref}
    used_atlases |= {region["atlas"] for region in by_class.get("Region", [])}
    missing = {"neuron types": sorted(used_neuron_types - neuron_types), "atlases": sorted(used_atlases - atlases)}
    assert missing == {"neuron types": [], "atlases": []}, missing


CLAIM_CLASSES = ("ConnectivityClaim", "HomologyClaim")
MOUSE, RAT, HUMAN = "NCBITaxon:10090", "NCBITaxon:10116", "NCBITaxon:9606"


def claims(cls: str) -> list[dict]:
    return [load(path) for path in VALID if target_class(path) == cls]


def enum_values(name: str) -> set[str]:
    from linkml_runtime import SchemaView

    return set(SchemaView(SCHEMA).get_enum(name).permissible_values)


def test_at_least_20_example_claims():
    count = sum(target_class(path) in CLAIM_CLASSES for path in VALID)
    assert count >= 20, count


def test_examples_cover_the_model():
    connectivity, homology = claims("ConnectivityClaim"), claims("HomologyClaim")
    measurements = [m for claim in connectivity for m in claim.get("measurements", [])]
    gaps = []
    for field, enum in [("predicate", "ConnectivityPredicate"), ("evidence_class", "EvidenceClass"),
                        ("result", "Result"), ("sign", "Sign")]:
        if missing := enum_values(enum) - {claim[field] for claim in connectivity}:
            gaps.append(f"{field}: {sorted(missing)}")
    if missing := enum_values("QuantityKind") - {m["quantity"] for m in measurements}:
        gaps.append(f"quantity: {sorted(missing)}")
    for keys in (("sd",), ("sem",), ("ci_low", "ci_high")):
        if not any(all(k in m for k in keys) for m in measurements):
            gaps.append(f"a measurement with {'/'.join(keys)}")
    checks = {
        "strength": any("strength" in c for c in connectivity),
        "a rat claim between UBERON regions": any(
            c["species"] == RAT and c["subject"]["id"].startswith("UBERON:") and c["object"]["id"].startswith("UBERON:")
            for c in connectivity),
        "two neuron-type claims": sum(c["subject"]["type"] == "neuron_type" for c in connectivity) >= 2,
        "extra": any("extra" in c for c in connectivity),
        "human curation": any(c["curation"]["by"] == "human" for c in connectivity),
        "agent curation with verification": any(c["curation"]["by"] == "agent" and "verification" in c for c in connectivity),
        "both correspondence values": {h["correspondence"] for h in homology} == enum_values("Correspondence"),
        "all confidence levels": {h["confidence"] for h in homology} == enum_values("Confidence"),
        "a mouse-rat homology": any({h["subject_species"], h["object_species"]} == {MOUSE, RAT} for h in homology),
        "a mouse-human homology": any({h["subject_species"], h["object_species"]} == {MOUSE, HUMAN} for h in homology),
        "prelimbic with anterior cingulate": any(
            {h["subject"]["id"], h["object"]["id"]} == {"MBA:972", "UBERON:0009835"} for h in homology),
    }
    gaps += [name for name, ok in checks.items() if not ok]
    assert gaps == [], gaps


def test_example_citations_use_the_test_prefix():
    not_test = [path.name for path in VALID
                if target_class(path) in CLAIM_CLASSES and not load(path)["source"]["doi"].startswith("10.5555/")]
    assert not_test == [], not_test
