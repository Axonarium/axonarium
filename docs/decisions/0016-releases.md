---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint 3.2)
---

# Releases: dumps on GitHub, DOIs from Zenodo's GitHub integration

## Context and Problem Statement

Tier 0 of the plan is "versioned data dumps on Zenodo and GitHub", each release citable by DOI, so that the project degrades to a frozen archive rather than disappearing (design principle 6). Sprint 3.2 asks for a release job that publishes the dumps and gets a DOI. The plan's building blocks name Zenodo's GitHub integration for DOIs. How is a release made, what does it hold, and how is it versioned?

## Considered Options

* A manually run workflow that rebuilds from empty, packages the dumps and publishes a GitHub release, which Zenodo's GitHub integration archives
* The same, but uploading the dumps to Zenodo through its REST API with a token
* A release on every merge to `main`

## Decision Outcome

Chosen option: "a manually run workflow, archived by Zenodo's GitHub integration", because the integration is the adopted building block and needs no secret: Zenodo archives each published GitHub release of an enabled repository and mints a DOI for it, plus one concept DOI for all versions.

* **Workflow:** `.github/workflows/release.yml`, run from the Actions tab on `main` with a version. It migrates an empty Postgres and runs the full build (`python -m build`, atlases and Allen claims included), so every release proves a full rebuild from empty passes (a v1 success criterion). It then packages the dumps (`python -m build.release`) and publishes the release with `gh release create`, tagging the commit it built. Its only permission is `contents: write`.
* **Contents:** `axonarium-<version>-dumps.zip` holds the dumps (`axonarium.json`, a CSV per table, `edges.graphml`, `retractions.json`, `manifest.json`), the CC BY 4.0 licence and a README with the commit and row counts. `SHA256SUMS` holds its checksum. The zip is byte-for-byte reproducible from the same dumps. As ADR 0005 requires, Allen-derived content (atlas regions and build-time connectivity claims) is left out; the dumps hold only the files' records.
* **On Zenodo:** the integration archives the release's source archive, which holds every data file, the schema and the code to rebuild the dumps. The dumps themselves are attached to the GitHub release. Zenodo takes the record's metadata from `CITATION.cff`.
* **Versions:** `vYYYY.MM.N`, the year and month of the release and then 0, 1 and so on for further releases that month (such as `v2026.10.0`). Data releases are dated, and the schema keeps its own version in `manifest.json`.
* **Cadence:** monthly, once Phase 6 starts (the Steward role), or whenever the maintainer wants one.

### Consequences

* Good, because releases need no secrets and no custom upload code, and the DOI comes from the integration the plan adopted.
* Good, because the Zenodo archive can rebuild every dump offline (`python -m build --no-atlases`), even if GitHub goes away.
* Bad, because the dumps are not themselves on Zenodo, only the files they are built from. If that matters later, the REST API option can add them, with a Zenodo token as a secret.
* Bad, because Zenodo reads one licence from `CITATION.cff` (Apache-2.0), while the archive's data is CC BY 4.0 (`REUSE.toml` declares each path). The maintainer may want to list both licences in `CITATION.cff`, a governance-file change.

### Confirmation

`build/tests/test_release.py` covers the package, its checksum, its reproducibility, the notes and the version format. The sprint's "done when" (a test release gets a DOI) needs the maintainer: enable `axonarium/axonarium` in Zenodo's GitHub settings (log in to Zenodo with GitHub as an organization owner), run the workflow, then add the concept DOI to `README.md` and `CITATION.cff`, and Zenodo to `SUCCESSION.md`.
