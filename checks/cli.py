"""Command line: `python -m checks files` and `python -m checks changes --base <ref>`."""

import argparse
from pathlib import Path

from checks.change_rules import check_changes
from checks.file_rules import check_file
from checks.findings import Finding
from checks.loading import load_tree
from checks.tree_rules import check_tree


def run_files(data_dir: Path) -> list[Finding]:
    """Every per-file and cross-file finding for the tree, sorted."""
    records, findings = load_tree(data_dir)
    for record in records:
        findings += check_file(record)
    findings += check_tree(records)
    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m checks", description="Check Axonarium's data files.")
    commands = parser.add_subparsers(dest="command", required=True)
    files = commands.add_parser("files", help="check every file under the data folder")
    files.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    changes = commands.add_parser("changes", help="check what changed since a git revision (deletions, retractions, the log)")
    changes.add_argument("--base", required=True, help="the git revision to compare against, such as origin/main")
    changes.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    args = parser.parse_args(argv)

    findings = run_files(args.data) if args.command == "files" else check_changes(args.data, args.base)
    for finding in findings:
        print(finding)
    return 1 if findings else 0
