---
status: accepted
date: 2026-10-03
decision-makers: Tyler Banks
---

# Serving database: read-shaped tables loaded with psycopg

## Context and Problem Statement

The files in `data/` are the source of truth, and every merge rebuilds the database that Supabase serves to the site, the REST API and the MCP server (design principles 1 and 2). LinkML generated a normalized PostgreSQL schema in sprint 0.2 (`schema/generated/axonarium.sql`). What tables should the live database have, and how does the build load them?

## Considered Options

* Read-shaped tables: one per record type, with typed columns for what readers filter on, JSONB for nested parts, and computed edges; loaded with psycopg
* LinkML's generated DDL, loaded with LinkML's `SQLStore`
* A single table of JSON documents

## Decision Outcome

Chosen option: "read-shaped tables", because Supabase turns tables directly into the public REST API, and these give readable endpoints (`/connectivity_claims?subject_id=eq.MBA:295`) without joins through surrogate keys.

* **Tables:** `atlases`, `regions`, `neuron_types`, `sources`, `connectivity_claims`, `homology_claims`, `edges` (computed from claims) and `retractions`, in the `public` schema. `build/tables.py` declares them; `build/README.md` lists them.
* **Loading:** one transaction drops and recreates only these tables, inserts every row with parameterized statements, enables row-level security with a read-only policy for Supabase's `anon` and `authenticated` roles, and asks the REST API to reload its schema. Readers see the old data or the new, never a mix, and the publishable key can read but never write.
* **Driver:** `psycopg[binary]` 3.3.6, a new dependency in the `build` group, because the standard library has no Postgres client.
* **Credentials:** the build reads the database URL from `AXONARIUM_DATABASE_URL`. In GitHub it is the `SUPABASE_DB_URL` secret of the `production` environment, which only jobs on `main` can open; it uses Supabase's session pooler, because GitHub's runners have no IPv6 and the direct host has no IPv4.
* LinkML's DDL stays in `schema/generated/` as the schema's reference SQL.

### Consequences

* Good, because the REST API is usable as it stands, and the tables stay close to the YAML files, so contributors can map one to the other.
* Good, because a failed load changes nothing.
* Bad, because the table declarations duplicate part of the schema; `build/tests` check that every record field lands in a column, and a schema change needs a matching change in `build/tables.py`.
* Neutral: LinkML's `SQLStore` was tried first and failed on this schema (LinkML 1.11.1), and its surrogate-key tables would have needed views to be readable.
