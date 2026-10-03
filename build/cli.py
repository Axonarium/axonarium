"""Command line: `python -m build [--data data] [--out dist] [--database URL]`."""

import argparse
import os
from pathlib import Path

from build.database import LoadFailed, load
from build.dumps import write_dumps
from build.tables import rows
from checks.cli import run_files
from checks.loading import load_tree


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m build",
                                     description="Rebuild the dumps and the database from the data files.")
    parser.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    parser.add_argument("--out", type=Path, default=Path("dist"), help="where to write the dumps (default: dist)")
    parser.add_argument("--database", help="a Postgres URL to load (default: the AXONARIUM_DATABASE_URL environment variable)")
    args = parser.parse_args(argv)

    # A typo in --data must never load an empty database over the real one.
    if not (args.data / "retractions.yaml").is_file():
        print(f"{args.data} is not a data folder (no retractions.yaml); build stopped")
        return 1
    findings = run_files(args.data)
    if findings:
        for finding in findings:
            print(finding)
        print(f"build stopped: {len(findings)} finding(s) above; nothing was written")
        return 1
    records, _ = load_tree(args.data)
    tables = rows(records)
    write_dumps(records, tables, args.out)
    url = args.database or os.environ.get("AXONARIUM_DATABASE_URL")
    if url:
        try:
            load(url, tables)
        except LoadFailed as error:
            print(error)
            return 1
    summary = ", ".join(f"{len(table)} {name}" for name, table in tables.items())
    print(f"built {args.out}: {summary}" + ("; loaded the database" if url else ""))
    return 0
