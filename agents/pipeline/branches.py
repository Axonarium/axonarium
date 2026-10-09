"""Results waiting on another branch (ADR 0028).

A run's results reach `main` only when its pull request merges. Until then a run started from `main` can't see them
and would send the same papers again. So before a step runs, every branch this checkout knows on its remotes is read
for that step's ledger. A row the branch itself wrote (one that differs from the ledger where the branch split from
this checkout's history) and that is newer than this checkout's row for the paper, or is for a paper this checkout has
no row for, is a result still waiting. A branch made before some results merged holds an older copy of the ledger, but
it didn't write those rows, so they don't count. The Literature workflow fetches every branch with its history first;
locally, `git fetch --prune` first.
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


def _rows(text: str) -> dict[str, dict]:
    return {row["key"]: row for row in csv.DictReader(io.StringIO(text)) if row.get("key")}


def _written(branch: str, path: str, theirs: dict[str, dict], run: Callable) -> dict[str, dict]:
    """The branch's rows that differ from the ledger where it split from this checkout's history: the rows it wrote.
    Without a common history to compare with, every row counts."""
    base = _git("merge-base", "HEAD", branch, run=run)
    if base.returncode != 0:
        return theirs
    shown = _git("show", f"{base.stdout.strip()}:{path}", run=run)
    before = _rows(shown.stdout) if shown.returncode == 0 else {}
    return {key: row for key, row in theirs.items() if before.get(key) != row}


def waiting(ledger: Ledger, run: Callable = subprocess.run) -> dict[str, int]:
    """{branch: papers} for each remote branch holding rows of this ledger that it wrote and this checkout lacks or
    has older."""
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
        written = _written(branch, path, _rows(shown.stdout), run)
        newer = sum(_newer(row, mine.get(key)) for key, row in written.items())
        if newer:
            found[branch] = newer
    return found


def refusal(step: str, found: dict[str, int]) -> str:
    """Why a step won't run while other branches hold its results."""
    listed = "; ".join(f"{branch} ({papers} paper(s))" for branch, papers in sorted(found.items()))
    return (f"other branches hold {step} results this checkout doesn't have yet: {listed}. Running now would send those "
            "papers again and pay for them twice. Merge their pull requests first (or delete a branch to discard its "
            "results), then run again; locally, `git fetch --prune` and update this checkout first.")
