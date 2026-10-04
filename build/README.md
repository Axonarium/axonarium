# Build

Turns the files in [data/](../data/) into dumps and the database the site reads. Nothing here is edited by hand: every merge to `main` rebuilds it all.

```bash
uv run python -m build                       # validate data/, write dist/
AXONARIUM_DATABASE_URL=postgresql://… uv run python -m build   # …and load Postgres
```

Options: `--data` (default `data`), `--out` (default `dist`), `--database` (default: the `AXONARIUM_DATABASE_URL` environment variable, so secrets stay off command lines), `--meshes DIR` (also write the 3D view's region meshes), `--http-cache DIR` (keep the answers of OLS, UBERON's bridges and the Allen API for seven days; CI uses it so an outage doesn't block merging, deploys don't). All of the build's HTTP goes through the online checks' retried, rate-limited session ([ADR 0012](../docs/decisions/0012-http-packages.md)).

1. **Validate:** every `checks files` rule. Any finding stops the build, and nothing is written.
2. **Atlases:** each atlas record with a BrainGlobe name is loaded at its pinned version (`ingest/atlases.py`), and its regions are mapped to UBERON by UBERON's bridges. The build stops if BrainGlobe serves another version, if data names a region its atlas lacks, or if an atlas resolves no amygdala region. Atlas regions go into the database, not the dumps ([ADR 0009](../docs/decisions/0009-atlas-layer.md)). `--no-atlases` skips this for offline work.
3. **Allen connectivity:** with the mouse atlas loaded, `ingest/allen_connectivity.py` makes region-level claims from wild-type experiments in the Allen Mouse Brain Connectivity Atlas: the targets of amygdala injections, and the amygdala targets of injections elsewhere. They pass the same rules as committed claims, go into the database, and never into the repository or the dumps ([ADR 0010](../docs/decisions/0010-allen-connectivity.md)).
4. **Meshes** (with `--meshes`): glTF meshes of every region a connection names, plus the brain outline and an `index.json` of names and centroids, from the pinned BrainGlobe atlas ([ADR 0011](../docs/decisions/0011-brain-viewer.md)). The deploy puts them in the site; they are never committed.
5. **Dumps:** written to a fresh folder, then moved into place.
6. **Database:** in one transaction, the tables below are emptied and refilled. A failed load changes nothing.

The tables are defined once, as SQLAlchemy tables in [tables.py](tables.py). Alembic migrations in [migrations/](migrations/) create them; the build never changes the schema. To change a table, edit `tables.py` and generate a migration (see [migrations/README](migrations/README)).

For the database tests, point `AXONARIUM_TEST_DATABASE_URL` at a scratch Postgres and migrate it first:

```bash
AXONARIUM_DATABASE_URL="$AXONARIUM_TEST_DATABASE_URL" uv run alembic upgrade head
uv run pytest build/tests
```

## Dumps

| File | Holds |
| --- | --- |
| `axonarium.json` | Every record, as a schema `KnowledgeBase` |
| `retractions.json` | The retractions log |
| `<table>.csv` | One per table: arrays and nested parts as JSON text |
| `edges.graphml` | The edge graph |
| `manifest.json` | Schema version and row counts |

## Tables

| Table | One row per |
| --- | --- |
| `atlases`, `regions`, `neuron_types`, `sources` | Record of that class |
| `connectivity_claims`, `homology_claims` | Claim; subject, object and citation flattened into columns, nested parts as JSONB |
| `edges` | Subject, predicate, object and species, aggregated from claims that aren't retracted: counts by result, evidence classes, strongest strength, strongest projection density, signs and claim IDs |
| `retractions` | Log entry, by position |
| `submissions` | The community inbox: a visitor's identifier for or against a claim ([ADR 0021](../docs/decisions/0021-community-inbox.md)). Closed to the public API, and never loaded, emptied or dumped by the build |

Claims carry `terms` (`cc-by-4.0`, or `allen-institute` for claims made from the Allen atlas; `build/terms.py`), and each edge lists its claims' terms, so the API can state what may be reused ([ADR 0013](../docs/decisions/0013-read-api.md)).

Columns are declared in [tables.py](tables.py). Why these tables, and not LinkML's generated SQL: [ADR 0008](../docs/decisions/0008-serving-database.md).

## Where it runs

- **CI** migrates and rebuilds an empty Postgres 17 on every pull request.
- **Deploy** (`.github/workflows/deploy.yml`) migrates and rebuilds Supabase on every push to `main`, from the `production` environment's `SUPABASE_DB_URL` secret, and exports the meshes for the site.
