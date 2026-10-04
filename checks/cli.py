"""Command line: `python -m checks files | changes --base <ref> | online [--base <ref>] | sources [--refresh]`."""

import argparse
from datetime import date
from pathlib import Path

from requests.adapters import BaseAdapter

from checks.change_rules import changed_since, check_changes
from checks.file_rules import check_file
from checks.findings import Finding
from checks.http import Fetcher
from checks.loading import load_tree
from checks.online_rules import check_online
from checks.sources import fill_sources
from checks.tree_rules import check_tree


def run_files(data_dir: Path) -> list[Finding]:
    """Every per-file and cross-file finding for the tree, sorted."""
    records, findings = load_tree(data_dir)
    for record in records:
        findings += check_file(record)
    findings += check_tree(records)
    return sorted(findings)


def main(argv: list[str] | None = None, transport: BaseAdapter | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m checks", description="Check Axonarium's data files.")
    commands = parser.add_subparsers(dest="command", required=True)
    files = commands.add_parser("files", help="check every file under the data folder")
    files.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    changes = commands.add_parser("changes", help="check what changed since a git revision (deletions, retractions, the log)")
    changes.add_argument("--base", required=True, help="the git revision to compare against, such as origin/main")
    changes.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    online = commands.add_parser("online", help="look identifiers and citations up in their registries (needs the network)")
    online.add_argument("--base", help="only check files changed since this git revision, such as origin/main")
    online.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    online.add_argument("--cache", type=Path, default=Path(".cache/checks"), help="where to cache answers (default: .cache/checks)")
    sources = commands.add_parser("sources", help="write a source record for every cited DOI that has none (needs the network)")
    sources.add_argument("--refresh", action="store_true", help="also re-fetch existing DOI records and rewrite those that changed")
    sources.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    sources.add_argument("--cache", type=Path, default=Path(".cache/checks"), help="where to cache answers (default: .cache/checks)")
    args = parser.parse_args(argv)

    if args.command == "files":
        findings = run_files(args.data)
    elif args.command == "changes":
        findings = check_changes(args.data, args.base)
    elif args.command == "online":
        records, _ = load_tree(args.data)
        scope = changed_since(args.data, args.base) if args.base else None
        findings = check_online(records, Fetcher(args.cache, transport), date.today(), scope)
    else:
        fetch = Fetcher(args.cache, transport, read_cache=not args.refresh)  # A refresh asks the registries again.
        written, findings = fill_sources(args.data, fetch, date.today(), args.refresh)
        for path in written:
            print(f"wrote {path}")
    for finding in findings:
        print(finding)
    return 1 if findings else 0
