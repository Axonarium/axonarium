"""Results waiting on another branch (ADR 0028).

A run's results reach `main` only when its pull request merges. Until then a run started from `main` can't see them
and would send the same papers again. So before a step runs, every branch this checkout knows on its remotes is read
for that step's ledger. A row newer than this checkout's row for the paper, or for a paper this checkout has no row
for, is a result still waiting. The Literature workflow fetches every branch first; locally, `git fetch --prune` first.
"""

import csv
import io
import subprocess
from collections.abc import Callable

from pipeline.corpus import ROOT, Ledger


def _git(*args: str, run: Callable = subprocess.run) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def remote_branches(run: Callable = subprocess.run) -> list[str]:
    """The remote branches this checkout knows, such as origin/literature/triage-2026-10-09-123."""
    listed = _git("for-each-ref", "--format=%(refname:short)", "refs/remotes/", run=run)
    if listed.returncode != 0:
        raise OSError(listed.stderr.strip() or "git for-each-ref failed")
    # refs/remotes/origin/HEAD is shortened to "origin": it only points at another branch.
    return [name for name in listed.stdout.split() if "/" in name and not name.endswith("/HEAD")]


def _newer(theirs: dict, mine: dict | None) -> bool:
    """Whether their row may be a result this checkout lacks. On the same day, any difference counts: refusing a run
    by mistake costs a branch deletion, while missing a result costs a second payment."""
    if mine is None or theirs.get("date", "") > mine.get("date", ""):
        return True
    return theirs.get("date", "") == mine.get("date", "") and any(theirs.get(k) != mine.get(k) for k in theirs.keys() & mine.keys())


def waiting(ledger: Ledger, run: Callable = subprocess.run) -> dict[str, int]:
    """{branch: papers} for each remote branch holding this ledger's rows that this checkout lacks or has older."""
    try:
        branches = remote_branches(run)
    except OSError:  # not a git checkout, or git missing: nothing to compare against
        return {}
    path = ledger.path.relative_to(ROOT).as_posix() if ledger.path.is_relative_to(ROOT) else ledger.path.name
    mine = ledger.read()
    found = {}
    for branch in branches:
        shown = _git("show", f"{branch}:{path}", run=run)
        if shown.returncode != 0:  # the branch has no such ledger
            continue
        newer = sum(_newer(row, mine.get(row["key"])) for row in csv.DictReader(io.StringIO(shown.stdout)) if row.get("key"))
        if newer:
            found[branch] = newer
    return found


def refusal(step: str, found: dict[str, int]) -> str:
    """Why a step won't run while other branches hold its results."""
    listed = "; ".join(f"{branch} ({papers} paper(s))" for branch, papers in sorted(found.items()))
    return (f"other branches hold {step} results this checkout doesn't have yet: {listed}. Running now would send those "
            "papers again and pay for them twice. Merge their pull requests first (or delete a branch to discard its "
            "results), then run again; locally, `git fetch --prune` and update this checkout first.")
