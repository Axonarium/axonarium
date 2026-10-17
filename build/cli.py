"""Command line: `python -m build [--data data] [--out dist] [--database URL] [--meshes DIR] [--snapshot FILE] [--report DIR]`."""

import argparse
import os
from pathlib import Path

from build import connectivity, gaps, meshes, reconcile, waxholm
from build import regions as atlas_regions
from build.database import LoadFailed, load
from build.dumps import write_dumps, write_snapshot
from build.tables import rows
from checks.cli import run_files
from checks.loading import load_tree
from ingest import atlases as atlas_source
from ingest import modules as module_list
from ingest.atlases import AMYGDALA_ROOT
from ingest.network import loaders


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


def main(argv: list[str] | None = None, atlas_loader=None, terms_loader=None, connectivity_loader=None,
         mesh_opener=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m build",
                                     description="Rebuild the dumps and the database from the data files.")
    parser.add_argument("--data", type=Path, default=Path("data"), help="the data folder (default: data)")
    parser.add_argument("--out", type=Path, default=Path("dist"), help="where to write the dumps (default: dist)")
    parser.add_argument("--database", help="a Postgres URL to load (default: the AXONARIUM_DATABASE_URL environment variable)")
    parser.add_argument("--no-atlases", action="store_true", help="don't load atlas regions from BrainGlobe (offline work)")
    parser.add_argument("--meshes", type=Path, help="also write glTF meshes of the connected regions here, for the site")
    parser.add_argument("--http-cache", type=Path, help="keep API answers here for seven days, so reruns (CI) don't depend on them")
    parser.add_argument("--snapshot", type=Path, help="also write every database row to this JSON file, for the site's fallback")
    parser.add_argument("--report", type=Path, help="also write the reconciliation report (agreement, conflict, silence) here")
    args = parser.parse_args(argv)

    url = args.database or os.environ.get("AXONARIUM_DATABASE_URL")
    if url and args.no_atlases:
        print("refusing to load a database with --no-atlases: it would empty the atlas regions; build without a database")
        return 1
    if args.meshes and args.no_atlases:
        print("--meshes needs the atlases; build without --no-atlases")
        return 1
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
    network = loaders(args.http_cache)  # OLS, UBERON's bridges and the Allen API, through one retried session
    terms_loader, atlas_loader = terms_loader or network[0], atlas_loader or network[1]
    connectivity_loader = connectivity_loader or network[2]
    tables = rows(records)
    modules = module_list.modules_of(records)  # data/modules.yaml (ADR 0034)
    loaded: dict[str, list[dict]] = {}
    terms: dict[str, dict[str, str]] = {}
    module_terms: dict[str, list[str]] = {}
    module_labels: dict[str, dict[str, str]] = {}
    atlases = [r.data for r in records if r.cls == "Atlas" and r.data.get("brainglobe_name")]
    if not args.no_atlases and atlases:
        try:
            terms = terms_loader(module_list.roots_of(modules))
        except Exception as error:  # OLS unreachable: the modules' regions can't be identified.
            print(f"loading the modules' UBERON terms from OLS failed: {error}; build stopped")
            return 1
        for atlas in atlases:
            try:
                loaded[atlas["id"]] = atlas_loader(atlas, terms)
            except Exception as error:  # BrainGlobe's S3, a UBERON bridge, or a pin: the build can't vouch for regions.
                print(f"atlas load failed for {atlas['id']} (BrainGlobe or UBERON bridge): {error}; build stopped")
                return 1
        module_terms = module_list.apply(modules, loaded, terms)
        module_labels = module_list.labels(module_terms, terms)
        problems = atlas_regions.unknown_regions(records, loaded)
        problems += [f"{atlas}: no amygdala regions; check the atlas and its UBERON bridge"
                     for atlas, region_rows in loaded.items() if region_rows and not atlas_regions.amygdala(region_rows)]
        problems += atlas_regions.module_problems(modules, loaded)
        for line in [str(p) for p in problems] or [atlas_regions.summary(a, r, modules) for a, r in loaded.items() if r]:
            print(line)
        if problems:
            print(f"build stopped: {len(problems)} atlas problem(s) above; nothing was written")
            return 1
    generated = []
    if loaded:
        try:
            generated = connectivity.allen_records(loaded, connectivity_loader)
        except Exception as error:  # The Allen API: the build can't vouch for the claims.
            print(f"Allen connectivity load failed: {error}; build stopped")
            return 1
        problems = connectivity.check_generated(records, generated) + atlas_regions.unknown_regions(generated, loaded)
        if problems:
            for problem in problems:
                print(problem)
            print(f"build stopped: {len(problems)} problem(s) in generated claims; nothing was written")
            return 1
        if generated:
            experiments = {record.data["extra"]["allen.experiment"] for record in generated}
            print(f"allen connectivity: {len(experiments)} experiment(s), {len(generated)} claim(s)")
    claims = [r.data for r in records + generated if r.cls == "ConnectivityClaim"]
    region_rows = [row for rows in loaded.values() for row in rows]
    found_gaps = gaps.find_gaps(claims, region_rows)  # gap mode (ADR 0027); none without the atlases
    if found_gaps:
        print(f"gaps: {len(found_gaps)} untested connection(s) from {len({g['subject_id'] for g in found_gaps})} region(s)")
    if args.meshes:
        drawn = meshes.regions_to_draw(records + generated, loaded, also=[gap["subject_id"] for gap in found_gaps])
        for atlas_id, region_ids in drawn.items():
            atlas = next(a for a in atlases if a["id"] == atlas_id)
            try:
                prefix = loaded[atlas_id][0]["id"].split(":")[0]
                amygdala = {f"{prefix}:{n}" for n in connectivity.amygdala_structures(loaded[atlas_id])}
                members = {row["id"]: row["modules"] for row in loaded[atlas_id] if row["modules"]}
                index = meshes.export_atlas(atlas, region_ids, args.meshes, amygdala=amygdala, modules=members,
                                            **({"open_atlas": mesh_opener} if mesh_opener else {}))
            except Exception as error:  # BrainGlobe's S3 or a pin: the site would show a brain without its regions.
                print(f"mesh export failed for {atlas_id}: {error}; build stopped")
                return 1
            print(f"meshes: {len(index['regions'])} region(s) of {atlas_id} in {args.meshes / atlas_id}")
        rat = next((a for a in atlases if a["id"] == waxholm.ATLAS), None)
        named = waxholm.rat_terms(records)
        if rat and named:  # rat claims name UBERON terms, drawn on Waxholm's structures (ADR 0034)
            try:
                bridge = waxholm.read_bridge()
                found = terms_loader([row["term"] for row in bridge])
                opened = (mesh_opener or atlas_source._open_brainglobe)(rat["brainglobe_name"],
                                                                        str(rat["extra"]["brainglobe.atlas_version"]))
                problems = waxholm.problems(bridge, opened.structures, found)
                for line in problems or waxholm.relabelled(bridge, found):
                    print(line)
                if problems:
                    print(f"build stopped: {len(problems)} problem(s) in the Waxholm bridge above; nothing was written")
                    return 1
                placed = waxholm.resolve(sorted(named), bridge, found)
                index = meshes.export_atlas(
                    rat, sorted(placed), args.meshes, open_atlas=lambda name, version: opened,
                    amygdala=set(terms.get(AMYGDALA_ROOT, {})),
                    modules={term: [m for m, members in module_terms.items() if term in members] for term in placed},
                    drawn_on={term: row["structure"] for term, row in placed.items()},
                    labels={term: label for under in found.values() for term, label in under.items()})
            except Exception as error:  # BrainGlobe, OLS or a pin: the rat's brain would lack its regions.
                print(f"mesh export failed for {waxholm.ATLAS}: {error}; build stopped")
                return 1
            left = sorted(set(named) - set(index["regions"]), key=lambda term: (-named[term], term))  # most named first
            shown = ", ".join(left[:10]) + (f" and {len(left) - 10} more" if len(left) > 10 else "")
            print(f"meshes: {len(index['regions'])} of {len(named)} rat region(s) drawn on {waxholm.ATLAS} in "
                  f"{args.meshes / waxholm.ATLAS}" + (f"; in the network view only: {shown}" if left else ""))
    # Dumps hold the files' records only: atlas regions, Allen claims and the gaps they suggest stay out (ADR 0005).
    write_dumps(records, tables, args.out)
    if args.report:
        reconcile.write_report(reconcile.reconcile(claims, region_rows), args.report)
    tables = {**atlas_regions.merge(rows(records + generated), loaded), "gaps": found_gaps}
    tables["modules"] = [{**row, "terms": module_terms.get(row["id"]), "labels": module_labels.get(row["id"]) or None}
                         for row in tables["modules"]]
    if args.snapshot:
        write_snapshot(tables, args.snapshot)
    if url:
        try:
            load(url, tables)
        except LoadFailed as error:
            print(error)
            return 1
    summary = ", ".join(f"{len(table)} {name}" for name, table in tables.items())
    print(f"built {args.out}: {summary}" + ("; loaded the database" if url else ""))
    return 0
