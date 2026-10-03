"""Rules about what a pull request changes: deletions and retractions need an entry in the log."""

import subprocess
from pathlib import Path

import yaml

from checks.findings import Finding
from checks.loading import class_for, load_tree

CLAIMS = ("ConnectivityClaim", "HomologyClaim")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def _at_base(root: Path, base: str, path: Path):
    """A file's YAML content at the base revision, or None if it didn't exist there."""
    shown = _git(root, "show", f"{base}:{path.as_posix()}")
    return yaml.safe_load(shown.stdout) if shown.returncode == 0 else None


def _entries(log) -> list:
    entries = log.get("entries") if isinstance(log, dict) else None
    return entries if isinstance(entries, list) else []


def check_changes(data_dir: Path, base: str) -> list[Finding]:
    data_dir = data_dir.resolve()
    top = _git(data_dir, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise SystemExit(f"{data_dir} is not inside a git repository")
    root = Path(top.stdout.strip())
    data_rel = data_dir.relative_to(root)
    log_path = data_dir / "retractions.yaml"

    diff = _git(root, "diff", "--name-status", "--find-renames", base, "--", data_rel.as_posix())
    if diff.returncode != 0:
        raise SystemExit(f"git diff against {base} failed: {diff.stderr.strip()}")

    removed, retracted = {}, {}
    for line in diff.stdout.splitlines():
        status, *paths = line.split("\t")
        old, new = Path(paths[0]), Path(paths[-1])
        if class_for(old.relative_to(data_rel)) not in CLAIMS:
            continue
        before = _at_base(root, base, old)
        if not isinstance(before, dict) or not isinstance(before.get("id"), str):
            continue
        if status.startswith(("D", "R")):
            removed[before["id"]] = old
        if status.startswith(("M", "R")) and before.get("status") != "retracted":
            after = yaml.safe_load((root / new).read_text(encoding="utf-8")) if (root / new).exists() else None
            if isinstance(after, dict) and after.get("status") == "retracted":
                retracted[before["id"]] = new

    records, _ = load_tree(data_dir)
    head_ids = {r.data.get("id") for r in records if r.cls in CLAIMS}
    head_log = yaml.safe_load(log_path.read_text(encoding="utf-8")) if log_path.exists() else None
    base_entries = _entries(_at_base(root, base, data_rel / "retractions.yaml"))
    head_entries = _entries(head_log)

    findings = []
    if head_entries[:len(base_entries)] != base_entries:
        findings.append(Finding(str(log_path), "log-rewritten",
                                "entries already in the base revision were edited, reordered or removed; only append"))
    new_entries = [e for e in head_entries[len(base_entries):] if isinstance(e, dict)]
    logged = {(e.get("claim"), e.get("action")) for e in new_entries}
    for claim_id, path in sorted(removed.items()):
        if claim_id not in head_ids and (claim_id, "deleted") not in logged:
            findings.append(Finding(str(root / path), "deletion-unlogged",
                                    f"{claim_id} was deleted without a new 'deleted' entry in data/retractions.yaml"))
    for claim_id, path in sorted(retracted.items()):
        if (claim_id, "retracted") not in logged:
            findings.append(Finding(str(root / path), "retraction-unlogged",
                                    f"{claim_id} was retracted without a new 'retracted' entry in data/retractions.yaml"))
    return sorted(findings)
