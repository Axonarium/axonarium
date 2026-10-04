"""A release's files (ADR 0016): the dumps, the data licence and a README in one zip, its checksum, and the notes.

Command line: `python -m build.release <version> --commit <sha> [--dist dist] [--out release]`, after `python -m build`.
"""

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

VERSION = re.compile(r"v20\d{2}\.(0[1-9]|1[0-2])\.(0|[1-9]\d*)")  # vYYYY.MM.N: the year and month, then 0, 1, …
LICENCE = Path(__file__).resolve().parents[1] / "LICENSES" / "CC-BY-4.0.txt"
STAMP = (1980, 1, 1, 0, 0, 0)  # every entry's time, so the same dumps always make the same zip


def notes(version: str, commit: str, manifest: dict) -> str:
    """The release notes, which the zip's README repeats."""
    counts = "\n".join(f"| {name} | {count} |" for name, count in manifest["tables"].items())
    return f"""Axonarium {version}: the knowledge base at commit {commit[:7]} ({commit}), rebuilt from its files.

| Table | Rows |
| --- | --- |
{counts}

`axonarium-{version}-dumps.zip` holds every record as JSON (`axonarium.json`), every table as CSV, the edge graph as \
GraphML (`edges.graphml`), the retractions log and `manifest.json` (schema version {manifest["schema_version"]}). \
`SHA256SUMS` holds its checksum.

**Licence:** CC BY 4.0. Credit Axonarium and the sources each claim cites. The connections the site and API make at \
build time from the Allen Mouse Brain Connectivity Atlas, and the atlases' regions, are not included: they carry the \
Allen Institute's terms (ADR 0005).

**Citing:** each release is archived on Zenodo with its own DOI; cite that DOI, or use CITATION.cff.
"""


def _zip(dist: Path, target: Path, folder: str, readme: str) -> None:
    def add(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
        entry = zipfile.ZipInfo(f"{folder}/{name}", date_time=STAMP)
        entry.compress_type, entry.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
        archive.writestr(entry, data)

    with zipfile.ZipFile(target, "w") as archive:
        for path in sorted(dist.iterdir()):
            add(archive, path.name, path.read_bytes())
        add(archive, "LICENSE.txt", LICENCE.read_bytes())
        add(archive, "README.md", readme.encode())


def package(dist: Path, out: Path, version: str, commit: str) -> list[Path]:
    """Write the zip, SHA256SUMS and NOTES.md to `out` (replacing it); return the files to attach to the release."""
    manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    text = notes(version, commit, manifest)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    zipped = out / f"axonarium-{version}-dumps.zip"
    _zip(dist, zipped, f"axonarium-{version}", text)
    sums = out / "SHA256SUMS"
    sums.write_text(f"{hashlib.sha256(zipped.read_bytes()).hexdigest()}  {zipped.name}\n", encoding="utf-8")
    (out / "NOTES.md").write_text(text, encoding="utf-8")
    return [zipped, sums]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m build.release", description="Package the dumps for a release.")
    parser.add_argument("version", help="the release's version, vYYYY.MM.N, such as v2026.10.0")
    parser.add_argument("--commit", required=True, help="the commit the dumps were built from")
    parser.add_argument("--dist", type=Path, default=Path("dist"), help="the dumps (default: dist)")
    parser.add_argument("--out", type=Path, default=Path("release"), help="where to write the release (default: release)")
    args = parser.parse_args(argv)
    if not VERSION.fullmatch(args.version):
        print(f"{args.version!r} is not a release version: use vYYYY.MM.N, such as v2026.10.0")
        return 1
    if not (args.dist / "manifest.json").is_file():
        print(f"{args.dist} holds no dumps (no manifest.json); run python -m build first")
        return 1
    for path in package(args.dist, args.out, args.version, args.commit):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
