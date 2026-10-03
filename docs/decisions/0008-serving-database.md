---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# Serving database: read-shaped tables, SQLAlchemy and Alembic

## Context and Problem Statement

The files in `data/` are the source of truth, and every merge rebuilds the database that Supabase serves to the site, the REST API and the MCP server (design principles 1 and 2). LinkML generated a normalized PostgreSQL schema in sprint 0.2 (`schema/generated/axonarium.sql`). What tables should the live database have, and how does the build load them?

## Considered Options

* Read-shaped tables: one per record type, with typed columns for what readers filter on, JSONB for nested parts, and computed edges; defined with SQLAlchemy, migrated with Alembic
* LinkML's generated DDL, loaded with LinkML's `SQLStore`
* A single table of JSON documents

## Decision Outcome

Chosen option: "read-shaped tables", because Supabase turns tables directly into the public REST API, and these give readable endpoints (`/connectivity_claims?subject_id=eq.MBA:295`) without joins through surrogate keys.

* **Tables:** `atlases`, `regions`, `neuron_types`, `sources`, `connectivity_claims`, `homology_claims`, `edges` (computed from claims) and `retractions`, in the `public` schema, defined once as SQLAlchemy tables in `build/tables.py`.
* **Schema:** Alembic migrations in `build/migrations/`, generated from those tables (`alembic revision --autogenerate`) and reviewed. CI and the deploy job run `alembic upgrade head` before every build, and CI also runs `alembic check`, which fails when `build/tables.py` and the migrations differ. The baseline migration enables row-level security with a read-only policy for Supabase's `anon` and `authenticated` roles and revokes every other privilege from them (autogenerate doesn't track policies, so they are written into the migration). Because Supabase gives its API roles full access to every new table in `public`, every table there, Alembic's own `alembic_version` included, gets row-level security; a test fails if one doesn't.
* **Loading:** the build never creates, alters or drops anything. In one transaction it empties the project's tables (without `cascade`, so a foreign key from anything else makes the load fail rather than touch it) and inserts every row with SQLAlchemy Core. Readers see the old data or the new, never a mix, and views or functions built on the tables survive. A database behind `build/tables.py` fails the load with a message naming `alembic upgrade head`.
* **Dependencies:** SQLAlchemy 2.1.3 (already in the environment through LinkML), Alembic 1.20.0 and `psycopg[binary]` 3.3.6 as SQLAlchemy's Postgres driver, in the `build` group. They are the standard Python tools for table definitions, migrations and Postgres access.
* **Credentials:** the build and Alembic read the database URL from `AXONARIUM_DATABASE_URL`; nothing is stored in `alembic.ini`. In GitHub it is the `SUPABASE_DB_URL` secret of the `production` environment, which only jobs on `main` can open; it uses Supabase's session pooler, because GitHub's runners have no IPv6 and the direct host has no IPv4.
* LinkML's DDL stays in `schema/generated/` as the schema's reference SQL.

### Consequences

* Good, because the REST API is usable as it stands, and the tables stay close to the YAML files, so contributors can map one to the other.
* Good, because a failed load changes nothing.
* Bad, because the tables restate part of the LinkML schema: a schema change needs `build/tables.py` and an Alembic migration. The build refuses a record field with no column, and a test walks every schema slot.
* Neutral: LinkML's `SQLStore` was tried first and failed on this schema (LinkML 1.11.1), and its surrogate-key tables would have needed views to be readable.
* Neutral: earlier drafts of this sprint dropped and recreated the tables on every load, then used hand-written Supabase CLI migrations that duplicated the table definitions; the maintainer asked for proper migrations with standard tools (3 October 2026).
