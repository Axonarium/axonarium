"""The build tests reuse the checks' valid data tree, and never see a real database URL."""

import pytest

from checks.tests.conftest import valid_tree  # noqa: F401 (a pytest fixture)


@pytest.fixture(autouse=True)
def no_database_url(monkeypatch):
    """An exported AXONARIUM_DATABASE_URL may be production; tests that need a database set it themselves."""
    monkeypatch.delenv("AXONARIUM_DATABASE_URL", raising=False)
