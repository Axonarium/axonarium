"""The build tests reuse the checks' valid data tree, and never see a real database URL."""

import pytest

from checks.tests.conftest import valid_tree  # noqa: F401 (a pytest fixture)


@pytest.fixture(autouse=True)
def no_database_url(monkeypatch):
    """An exported AXONARIUM_DATABASE_URL may be production; tests that need a database set it themselves."""
    monkeypatch.delenv("AXONARIUM_DATABASE_URL", raising=False)


@pytest.fixture(autouse=True)
def no_network_atlases(monkeypatch):
    """Tests never reach BrainGlobe or UBERON: a build that would load real atlases fails instead."""
    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to load a real atlas; pass --no-atlases or an atlas_loader")
    monkeypatch.setattr("ingest.atlases._open_brainglobe", refuse)
    monkeypatch.setattr("ingest.atlases._download", refuse)
    monkeypatch.setattr("ingest.atlases._get_json", refuse)
