"""Every test's ledgers live in its own temporary folder, so no test can write to corpus/."""

from types import SimpleNamespace

import pytest

from pipeline import branches, cli, extract, triage, verify


@pytest.fixture(autouse=True)
def ledgers_in_tmp(tmp_path, monkeypatch):
    for ledger in (triage.LEDGER, extract.LEDGER, verify.LEDGER):
        monkeypatch.setattr(ledger, "path", tmp_path / "ledgers" / ledger.path.name)
    # This checkout's own remote branches are no test's business; test_triage checks the guard itself.
    monkeypatch.setattr(cli, "branches", SimpleNamespace(waiting=lambda ledger: {}, refusal=branches.refusal))
