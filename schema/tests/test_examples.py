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
