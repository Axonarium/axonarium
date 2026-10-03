"""Rules that look at one data file at a time."""

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


RULES = [_schema, _file_name]


def check_file(record: Record) -> list[Finding]:
    return [finding for rule in RULES for finding in rule(record)]
