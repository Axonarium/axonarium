"""Rules about what a branch changes: deletions, retractions and restorations need a log entry."""

import subprocess
from pathlib import Path

from checks.findings import Finding
from checks.loading import class_for, load_tree, parse_yaml

CLAIMS = ("ConnectivityClaim", "HomologyClaim")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=root, capture_output=True, text=True)


def _yaml(text: str):
    try:
        return parse_yaml(text)
    except Exception:  # Malformed files are the `files` command's business; here they simply prove nothing.
        return None


def _at(root: Path, revision: str, path: Path):
    shown = _git(root, "show", f"{revision}:{path.as_posix()}")
    return _yaml(shown.stdout) if shown.returncode == 0 else None


def _entries(log) -> list:
    entries = log.get("entries") if isinstance(log, dict) else None
    return entries if isinstance(entries, list) else []


def _changed_paths(root: Path, base: str, data_rel: Path) -> list[Path]:
    """Every path under data/ that existed at the base revision and differs now (renames give their old path)."""
    diff = _git(root, "diff", "-z", "--no-color", "--name-status", "--find-renames", base, "--", data_rel.as_posix())
    if diff.returncode != 0:
        raise SystemExit(f"git diff against {base} failed: {diff.stderr.strip()}")
    fields, paths = diff.stdout.split("\0"), []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        count = 2 if status[0] in "RC" else 1
        old = fields[i + 1]
        if status[0] != "A":
            paths.append(Path(old))
        i += 1 + count
    return paths


def check_changes(data_dir: Path, base: str) -> list[Finding]:
    data_dir = data_dir.resolve()
    top = _git(data_dir, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise SystemExit(f"{data_dir} is not inside a git repository")
    root = Path(top.stdout.strip())
    data_rel = data_dir.relative_to(root)
    merge_base = _git(root, "merge-base", base, "HEAD")
    if merge_base.returncode != 0:
        raise SystemExit(f"can't find where this branch left {base}: {merge_base.stderr.strip()}")
    since = merge_base.stdout.strip()  # Changes that landed on the base after the branch started aren't ours.

    before = {}
    for path in _changed_paths(root, since, data_rel):
        if class_for(path.relative_to(data_rel)) in CLAIMS:
            record = _at(root, since, path)
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                before[record["id"]] = (path, record.get("status"))

    records, _ = load_tree(data_dir)
    now = {r.data["id"]: r for r in records if r.cls in CLAIMS and isinstance(r.data.get("id"), str)}

    log_path = data_dir / "retractions.yaml"
    base_entries = _entries(_at(root, since, data_rel / "retractions.yaml"))
    head_entries = _entries(_yaml(log_path.read_text(encoding="utf-8"))) if log_path.exists() else []
    findings = []
    if head_entries[:len(base_entries)] != base_entries:
        findings.append(Finding(str(log_path), "log-rewritten",
                                "entries already on the base branch were edited, reordered or removed; only append"))
    logged = {(e.get("claim"), e.get("action")) for e in head_entries[len(base_entries):]
              if isinstance(e, dict) and isinstance(e.get("claim"), str) and isinstance(e.get("action"), str)}

    for claim_id, (path, status_before) in sorted(before.items()):
        current = now.get(claim_id)
        if current is None:
            needed, rule, what = "deleted", "deletion-unlogged", "deleted"
            where = root / path
        else:
            status_now = current.data.get("status")
            if status_now == "retracted" and status_before != "retracted":
                needed, rule, what = "retracted", "retraction-unlogged", "retracted"
            elif status_before == "retracted" and status_now != "retracted":
                needed, rule, what = "restored", "restoration-unlogged", "restored"
            else:
                continue
            where = current.path
        if (claim_id, needed) not in logged:
            findings.append(Finding(str(where), rule, f"{claim_id} was {what} without a new '{needed}' entry in data/retractions.yaml"))
    return sorted(findings)
