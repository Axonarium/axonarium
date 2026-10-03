"""The `changes` command: deletions and retractions need a log entry, and the log is append-only."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from checks.change_rules import check_changes
from checks.cli import main

CLAIM = Path("claims", "examples", "clm-pq22bk4dtz.yaml")
ENTRY = {"claim": "clm-pq22bk4dtz", "reason": "Test.",
         "curation": {"by": "human", "orcid": "0000-0002-1825-0097", "role": "curator", "date": "2026-10-03"}}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *args],
                   cwd=repo, check=True, capture_output=True)


@pytest.fixture
def data(valid_tree) -> Path:
    """The valid tree, committed as the base revision of a fresh git repository."""
    repo = valid_tree.parent
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return valid_tree


def write_log(data: Path, *entries: dict) -> None:
    (data / "retractions.yaml").write_text(yaml.safe_dump({"entries": list(entries)}, sort_keys=False), encoding="utf-8")


def rules(data: Path) -> list[str]:
    return sorted(f.rule for f in check_changes(data, "main"))


def test_changes_without_data_changes(data):
    assert rules(data) == []


def test_deleted_claim_needs_log(data):
    (data / CLAIM).unlink()
    assert rules(data) == ["deletion-unlogged"]


def test_deleted_claim_with_log_passes(data):
    (data / CLAIM).unlink()
    write_log(data, {**ENTRY, "action": "deleted"})
    assert rules(data) == []


def test_retraction_needs_log(data):
    path = data / CLAIM
    path.write_text(path.read_text().replace("status: accepted", "status: retracted"), encoding="utf-8")
    assert rules(data) == ["retraction-unlogged"]


def test_retraction_with_log_passes(data):
    path = data / CLAIM
    path.write_text(path.read_text().replace("status: accepted", "status: retracted"), encoding="utf-8")
    write_log(data, {**ENTRY, "action": "retracted"})
    assert rules(data) == []


def test_log_entry_removed(data):
    write_log(data, {**ENTRY, "action": "deleted"})
    git(data.parent, "commit", "-q", "-am", "log an entry")
    write_log(data)
    assert rules(data) == ["log-rewritten"]


def test_log_entry_edited(data):
    write_log(data, {**ENTRY, "action": "deleted"})
    git(data.parent, "commit", "-q", "-am", "log an entry")
    write_log(data, {**ENTRY, "action": "deleted", "reason": "Changed."})
    assert rules(data) == ["log-rewritten"]


def test_base_without_log(data):
    git(data.parent, "rm", "-q", str(data / "retractions.yaml"))
    git(data.parent, "commit", "-q", "-m", "no log yet")
    (data / CLAIM).unlink()
    assert rules(data) == ["deletion-unlogged"]
    write_log(data, {**ENTRY, "action": "deleted"})
    assert rules(data) == []


def test_moved_claim_is_not_a_deletion(data):
    moved = data / "claims" / "amygdala" / CLAIM.name
    moved.parent.mkdir(parents=True)
    shutil.move(data / CLAIM, moved)
    assert rules(data) == []


def test_cli_changes(data, capsys):
    assert main(["changes", "--base", "main", "--data", str(data)]) == 0
    (data / CLAIM).unlink()
    assert main(["changes", "--base", "main", "--data", str(data)]) == 1
    assert ": deletion-unlogged: " in capsys.readouterr().out
