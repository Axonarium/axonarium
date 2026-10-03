"""Rules that look at one data file at a time."""

import math
import re
from collections.abc import Iterator
from functools import cache
from pathlib import Path

from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin

from checks.findings import Finding, Record
from checks.loading import expected_file_name

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "axonarium.yaml"


@cache
def _validator() -> Validator:
    return Validator(str(SCHEMA), validation_plugins=[JsonschemaValidationPlugin(closed=True)])


def _schema(record: Record) -> list[Finding]:
    report = _validator().validate(record.data, record.cls)
    return [Finding(str(record.path), "schema", r.message) for r in report.results
            if getattr(r.severity, "name", r.severity) == "ERROR"]


def _file_name(record: Record) -> list[Finding]:
    record_id = record.data.get("id")
    expected = expected_file_name(record.cls, record_id) if isinstance(record_id, str) else None
    if expected and record.path.name != expected:
        return [Finding(str(record.path), "file-name", f"a {record.cls} with ID {record_id} must be named {expected}")]
    return []


EXTRA_KEY = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_.]+$")
CLAIMS = ("ConnectivityClaim", "HomologyClaim")
# Unit, and the range a value must lie in, for each quantity kind.
QUANTITIES = {
    "connection_probability": ("1", 0, 1),
    "projection_density": ("1", 0, 1),
    "fraction_of_labelled_neurons": ("1", 0, 1),
    "synapse_count": ("1", 0, math.inf),
    "conduction_delay": ("ms", 0, math.inf),
}


def _walk(value, where: str = "") -> Iterator[tuple[str, object]]:
    """Every value in a nested record, with a JSON-pointer-like path."""
    yield where or "/", value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{where}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{where}/{index}")


def _finding(record: Record, rule: str, message: str) -> Finding:
    return Finding(str(record.path), rule, message)


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _measurements(record: Record) -> list[tuple[int, dict]]:
    items = record.data.get("measurements")
    return [(i, m) for i, m in enumerate(items) if isinstance(m, dict)] if isinstance(items, list) else []


def _finite(value) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, float) and math.isfinite(value))


def _extra_mapping(record: Record) -> list[Finding]:
    if "extra" in record.data and not isinstance(record.data["extra"], dict):
        return [_finding(record, "extra-mapping", "extra must be a mapping of namespaced keys to values")]
    return []


def _extra_key(record: Record) -> list[Finding]:
    return [_finding(record, "extra-key", f"extra key {key!r} must be namespaced, like lab.tracer")
            for key in _mapping(record.data.get("extra")) if not (isinstance(key, str) and EXTRA_KEY.match(key))]


def _empty_text(record: Record) -> list[Finding]:
    data = {key: value for key, value in record.data.items() if key != "extra"}
    return [_finding(record, "empty-text", f"empty text at {where}")
            for where, value in _walk(data) if isinstance(value, str) and not value.strip()]


def _non_finite(record: Record) -> list[Finding]:
    return [_finding(record, "non-finite", f"{value} at {where} is not a finite number")
            for where, value in _walk(record.data)
            if isinstance(value, float) and not math.isfinite(value)]


def _uncertainty(record: Record) -> list[Finding]:
    findings = []
    for i, m in _measurements(record):
        for key in ("sd", "sem"):
            if _finite(m.get(key)) and m[key] < 0:
                findings.append(_finding(record, "uncertainty", f"measurements/{i}/{key} is negative"))
        if ("ci_low" in m) != ("ci_high" in m):
            findings.append(_finding(record, "uncertainty", f"measurements/{i} needs both ci_low and ci_high"))
        elif _finite(m.get("ci_low")) and _finite(m.get("ci_high")) and m["ci_low"] > m["ci_high"]:
            findings.append(_finding(record, "uncertainty", f"measurements/{i} has ci_low above ci_high"))
    return findings


def _unit(record: Record) -> list[Finding]:
    findings = []
    for i, m in _measurements(record):
        if m.get("quantity") not in QUANTITIES:
            continue
        unit, low, high = QUANTITIES[m["quantity"]]
        if m.get("unit") != unit:
            findings.append(_finding(record, "unit", f"measurements/{i}: {m['quantity']} uses unit {unit!r}, not {m.get('unit')!r}"))
        if _finite(m.get("value")) and not low <= m["value"] <= high:
            findings.append(_finding(record, "unit", f"measurements/{i}: {m['quantity']} must lie in [{low}, {high}]"))
    return findings


def _absent_result(record: Record) -> list[Finding]:
    data = record.data
    if record.cls != "ConnectivityClaim" or data.get("result") != "absent":
        return []
    problems = [label for label, bad in (
        ("a strength", "strength" in data),
        ("measurements", bool(data.get("measurements"))),
        ("a sign other than unknown", data.get("sign", "unknown") != "unknown"),
    ) if bad]
    return [_finding(record, "absent-result", f"an absent result can't have {problem}") for problem in problems]


def _role(record: Record) -> list[Finding]:
    if record.cls not in CLAIMS and record.cls != "RetractionLog":
        return []
    curations = [("curation", _mapping(record.data.get("curation")))]
    if record.cls == "RetractionLog" and isinstance(record.data.get("entries"), list):
        curations = [(f"entries/{i}/curation", _mapping(e.get("curation"))) for i, e in enumerate(record.data["entries"])
                     if isinstance(e, dict)]
    findings = []
    for where, curation in curations:
        by, role = curation.get("by"), curation.get("role")
        if (by == "human" and role != "curator") or (by == "agent" and role in ("curator", "verifier")):
            findings.append(_finding(record, "role", f"{where}: a {by} can't curate in the role {role!r}"))
    verification = _mapping(record.data.get("verification"))
    if verification and verification.get("role") != "verifier":
        findings.append(_finding(record, "role", f"verification: the role must be verifier, not {verification.get('role')!r}"))
    return findings


def _independent_verifier(record: Record) -> list[Finding]:
    curation, verification = _mapping(record.data.get("curation")), _mapping(record.data.get("verification"))
    if curation.get("by") == verification.get("by") == "agent" and curation.get("prompt") == verification.get("prompt"):
        return [_finding(record, "independent-verifier", "the verifier ran the same prompt as the extractor")]
    return []


def _doi_case(record: Record) -> list[Finding]:
    dois = [_mapping(record.data.get("source")).get("doi")]
    if record.cls == "Source" and isinstance(record.data.get("id"), str) and record.data["id"].startswith("doi:"):
        dois.append(record.data["id"])
    return [_finding(record, "doi-case", f"DOI {doi!r} must be lowercase")
            for doi in dois if isinstance(doi, str) and doi != doi.lower()]


def _homology_pair(record: Record) -> list[Finding]:
    if record.cls != "HomologyClaim":
        return []
    data, findings = record.data, []
    if data.get("subject_species") and data.get("subject_species") == data.get("object_species"):
        findings.append(_finding(record, "homology-pair", "homology links two different species"))
    kinds = {_mapping(data.get("subject")).get("type"), _mapping(data.get("object")).get("type")}
    if len(kinds - {None}) > 1:
        findings.append(_finding(record, "homology-pair", "homology links two entities of the same kind"))
    return findings


def _neuron_type_region(record: Record) -> list[Finding]:
    if record.cls == "NeuronType" and _mapping(record.data.get("region")).get("type") not in (None, "region"):
        return [_finding(record, "neuron-type-region", "a neuron type's region must be a region")]
    return []


# These assume the record's types are right, so they run only once the schema check passes.
SEMANTIC_RULES = [_extra_mapping, _extra_key, _empty_text, _non_finite, _uncertainty, _unit, _absent_result,
                  _role, _independent_verifier, _doi_case, _homology_pair, _neuron_type_region]


def check_file(record: Record) -> list[Finding]:
    findings = _schema(record) + _file_name(record)
    if any(f.rule == "schema" for f in findings):
        return findings
    return findings + [finding for rule in SEMANTIC_RULES for finding in rule(record)]
