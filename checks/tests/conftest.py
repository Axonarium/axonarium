"""Shared fixtures: a valid data tree built from the schema's examples."""

import shutil
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "schema" / "examples" / "valid"
BROKEN = Path(__file__).parent / "fixtures" / "broken"


def _data_path(cls: str, record: dict, example: Path) -> Path | None:
    """Where an example belongs in data/, following the layout in data/README.md."""
    if cls == "ConnectivityClaim":
        return Path("claims", "examples", f"{record['id']}.yaml")
    if cls == "HomologyClaim":
        return Path("homology", f"{record['id']}.yaml")
    if cls == "Atlas":
        return Path("entities", "atlases", f"{record['id']}.yaml")
    if cls == "Region":
        return Path("entities", "regions", f"{record['id'].replace(':', '_')}.yaml")
    if cls == "NeuronType":
        return Path("entities", "neuron_types", f"{record['id']}.yaml")
    if cls == "Source":
        return Path("sources", example.name.split("-", 1)[1])
    return None  # RetractionLog: the valid tree starts with an empty log


@pytest.fixture
def valid_tree(tmp_path) -> Path:
    data = tmp_path / "data"
    for example in sorted(EXAMPLES.glob("*.yaml")):
        cls = example.name.split("-", 1)[0]
        target = _data_path(cls, yaml.safe_load(example.read_text(encoding="utf-8")), example)
        if target:
            (data / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(example, data / target)
    (data / "retractions.yaml").write_text("entries: []\n", encoding="utf-8")
    return data


def overlay(data_dir: Path, fixture: Path) -> None:
    """Copy a broken fixture's files over the data tree."""
    shutil.copytree(fixture, data_dir, dirs_exist_ok=True)
