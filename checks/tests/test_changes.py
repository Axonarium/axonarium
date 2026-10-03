"""The `changes` command: deletions and retractions need a log entry, and the log is append-only."""

import copy
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
    # Deep copies, so PyYAML doesn't emit anchors for shared objects; data files may not use them.
    plain = [copy.deepcopy(e) for e in entries]
    (data / "retractions.yaml").write_text(yaml.safe_dump({"entries": plain}, sort_keys=False), encoding="utf-8")


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


# Fixes from the final review.

def test_moved_reformatted_retraction_is_caught(data):
    """git sees an add plus a delete (too different to be a rename); the claim's ID still decides."""
    record = yaml.safe_load((data / CLAIM).read_text())
    (data / CLAIM).unlink()
    moved = data / "claims" / "amygdala" / CLAIM.name
    moved.parent.mkdir(parents=True)
    moved.write_text(yaml.safe_dump({**record, "status": "retracted"}, default_flow_style=True), encoding="utf-8")
    git(data.parent, "add", "-A")
    assert rules(data) == ["retraction-unlogged"]


def test_tracked_move_is_not_a_deletion(data):
    moved = data / "claims" / "amygdala" / CLAIM.name
    moved.parent.mkdir(parents=True)
    git(data.parent, "mv", str(data / CLAIM), str(moved))
    assert rules(data) == []


def test_symlink_replacing_a_claim_is_a_deletion(data):
    (data / CLAIM).unlink()
    (data / CLAIM).symlink_to("/nonexistent/clm.yaml")
    git(data.parent, "add", "-A")
    assert rules(data) == ["deletion-unlogged"]


def test_branch_behind_main_has_no_false_findings(data):
    """Changes that landed on main after the branch started aren't the branch's changes."""
    repo = data.parent
    git(repo, "branch", "feature")
    added = data / "claims" / "examples" / "clm-zzzzzzzz22.yaml"
    added.write_text((data / CLAIM).read_text().replace("clm-pq22bk4dtz", "clm-zzzzzzzz22"), encoding="utf-8")
    write_log(data, {**ENTRY, "claim": "clm-fm6qfyqfye", "action": "deleted"})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "main moves on")
    git(repo, "switch", "-q", "feature")
    assert rules(data) == []


def test_unretraction_needs_log(data):
    path = data / CLAIM
    path.write_text(path.read_text().replace("status: accepted", "status: retracted"), encoding="utf-8")
    write_log(data, {**ENTRY, "action": "retracted"})
    git(data.parent, "commit", "-q", "-am", "retract")
    path.write_text(path.read_text().replace("status: retracted", "status: accepted"), encoding="utf-8")
    assert rules(data) == ["restoration-unlogged"]
    write_log(data, {**ENTRY, "action": "retracted"}, {**ENTRY, "action": "restored"})
    assert rules(data) == []


def test_odd_changes_dont_crash(data):
    weird = data / "claims" / "amygdalä"
    weird.mkdir()
    shutil.move(data / CLAIM, weird / CLAIM.name)
    (data / "claims" / "examples" / "clm-vq53bgcgt4.yaml").write_text("id: [unclosed\n", encoding="utf-8")
    (data / "retractions.yaml").write_text("entries:\n  - claim: [a, b]\n    action: deleted\n", encoding="utf-8")
    git(data.parent, "add", "-A")
    found = rules(data)  # must not raise; the unparseable claim can't prove it still exists
    assert "deletion-unlogged" in found
