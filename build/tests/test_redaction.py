"""A failed load never shows the database password, however the URL is written. No database needed."""

import pytest

from build.database import LoadFailed, load
from build.tables import TABLES


@pytest.mark.parametrize("url, secrets", [
    ("postgresql://axonarium:hunter2-secret@127.0.0.1:1/nowhere?connect_timeout=2", ["hunter2-secret"]),
    # An unencoded @ in the password: libpq and Python's URL parser split it differently.
    ("postgresql://postgres.ref:Tr0ub4dor@3xyz@127.0.0.1:1/nowhere?connect_timeout=2", ["Tr0ub4dor", "3xyz"]),
    # No scheme: libpq echoes the whole string in its error.
    ("postgres.ref:hunter2-secret@127.0.0.1:1/nowhere", ["hunter2-secret"]),
    # A character Python's URL parser rejects outright.
    ("postgresql://postgres.ref:pa[ss-secret@127.0.0.1:1/nowhere?connect_timeout=2", ["pa[ss-secret", "ss-secret"]),
], ids=["plain", "unencoded-at", "no-scheme", "bracket"])
def test_failure_never_shows_the_password(url, secrets):
    with pytest.raises(LoadFailed) as error:
        load(url, {name: [] for name in TABLES})
    assert not any(secret in str(error.value) for secret in secrets), str(error.value)
