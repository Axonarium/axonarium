# Build

Turns the files in [data/](../data/) into dumps and the database the site reads. Nothing here is edited by hand: every merge to `main` rebuilds it all.

```bash
uv run python -m build                       # validate data/, write dist/
AXONARIUM_DATABASE_URL=postgresql://… uv run python -m build   # …and load Postgres
```

Options: `--data` (default `data`), `--out` (default `dist`), `--database` (default: the `AXONARIUM_DATABASE_URL` environment variable, so secrets stay off command lines).

1. **Validate:** every `checks files` rule. Any finding stops the build, and nothing is written.
2. **Dumps:** written to a fresh folder, then moved into place.
3. **Database:** in one transaction, the tables below are emptied and refilled. A failed load changes nothing.

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
| `edges` | Subject, predicate, object and species, aggregated from claims that aren't retracted: counts by result, evidence classes, strongest strength, signs and claim IDs |
| `retractions` | Log entry, by position |

Columns are declared in [tables.py](tables.py). Why these tables, and not LinkML's generated SQL: [ADR 0008](../docs/decisions/0008-serving-database.md).

## Where it runs

- **CI** migrates and rebuilds an empty Postgres 17 on every pull request.
- **Deploy** (`.github/workflows/deploy.yml`) migrates and rebuilds Supabase on every push to `main`, from the `production` environment's `SUPABASE_DB_URL` secret.
