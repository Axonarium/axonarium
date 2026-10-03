"""Command line: `python -m build [--data data] [--out dist] [--database URL]`."""

import argparse
import os
from pathlib import Path

from build import regions as atlas_regions
from build.database import LoadFailed, load
from build.dumps import write_dumps
from build.tables import rows
from checks.cli import run_files
from checks.loading import load_tree
from ingest.atlases import load_atlas


def _unsafe_out(out: Path, data: Path) -> str | None:
    """Why the dumps folder must not be replaced, or None. Replacing it deletes everything in it."""
    out, data, here = out.resolve(), data.resolve(), Path.cwd().resolve()
    if out == here or out in here.parents:
        return "it is the working folder or contains it"
    if out == data or data in out.parents or out in data.parents:
        return "it overlaps the data folder"
    if out.exists() and (not out.is_dir() or (any(out.iterdir()) and not (out / "manifest.json").is_file())):
        return "it holds files that aren't a previous build (no manifest.json)"
    return None


def main(argv: list[str] | None = None, atlas_loader=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m build",
                                     description="Rebuild the dumps and the database from the data files.")
    parser.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    parser.add_argument("--out", type=Path, default=Path("dist"), help="where to write the dumps (default: dist)")
    parser.add_argument("--database", help="a Postgres URL to load (default: the AXONARIUM_DATABASE_URL environment variable)")
    parser.add_argument("--no-atlases", action="store_true", help="don't load atlas regions from BrainGlobe (offline work)")
    args = parser.parse_args(argv)

    unsafe = _unsafe_out(args.out, args.data)
    if unsafe:
        print(f"refusing to write dumps to {args.out}: {unsafe}")
        return 1
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
    loaded: dict[str, list[dict]] = {}
    if not args.no_atlases:
        loader = atlas_loader or load_atlas
        for atlas in (r.data for r in records if r.cls == "Atlas" and r.data.get("brainglobe_name")):
            try:
                loaded[atlas["id"]] = loader(atlas)
            except Exception as error:  # Network, BrainGlobe or a pin mismatch: the build can't vouch for regions.
                print(f"atlas load failed for {atlas['id']}: {error}; build stopped (use --no-atlases to work offline)")
                return 1
        problems = atlas_regions.unknown_regions(records, loaded)
        problems += [f"{atlas}: no amygdala regions; check the atlas and its UBERON bridge"
                     for atlas, region_rows in loaded.items() if region_rows and not atlas_regions.amygdala(region_rows)]
        for line in [str(p) for p in problems] or [atlas_regions.summary(a, r) for a, r in loaded.items() if r]:
            print(line)
        if problems:
            print(f"build stopped: {len(problems)} atlas problem(s) above; nothing was written")
            return 1
    write_dumps(records, tables, args.out)  # The files' records only: atlas-derived regions stay out of dumps.
    tables = atlas_regions.merge(tables, loaded)
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
