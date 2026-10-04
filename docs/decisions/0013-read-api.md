---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
---

# Read API: JSON routes on the site, an OpenAPI 3.1 contract, and reuse terms on every claim

## Context and Problem Statement

Sprint 3.1 asks for a documented read API, which the MCP server (3.4) and other clients build on. The serving database already has Supabase's generated REST API, but it exposes table layouts, not a stable contract, and its free tier has no edge cache. Some claims (Allen-derived, ADR 0005 and 0010) may be shown and served but not redistributed under CC BY. How is the API built, and how does a client know what it may do with each claim?

## Considered Options

* JSON route handlers in the Next.js site under `/api/v1`, with a hand-written OpenAPI 3.1 contract and responses tested against it
* Supabase's REST API (PostgREST) as the public API, documented with its generated OpenAPI
* A separate API service (FastAPI or similar)

## Decision Outcome

Chosen option: "route handlers in the site", because they reuse the site's data layer, run on the same Vercel deployment and edge cache, and keep the table layout private behind a contract that can stay stable while the tables change.

* **Endpoints:** `/api/v1` (index), `/openapi.json`, `/regions` (search by name or acronym, atlas, amygdala; paged), `/regions/{id}` (with subregions, outputs and inputs), `/connections` (filters by subject, object, species, predicate and minimum density; strongest density first; paged), `/connections/{id}` (with every claim), `/claims/{id}` and `/sources/{id}`.
* **Contract:** the OpenAPI 3.1 document lives in `site/lib/openapi.ts` and is served at `/api/v1/openapi.json`. The response shapes are pure functions (`site/lib/api.ts`); Vitest checks each one against the contract's schemas with Ajv.
* **Caching and errors:** responses are cached at Vercel's edge for five minutes (`s-maxage=300`, stale for up to an hour while revalidating) and allow any origin. Bad parameters give 400, unknown IDs 404, an unreadable database 503, each with an `error` message.
* **Reuse terms:** the build records each claim's terms in the serving tables (`terms`: `cc-by-4.0` for claims in the repository, `allen-institute` for claims made from the Allen atlas; `build/terms.py`), and each connection lists its claims' terms. The API returns, with every claim, the terms' name, URL and a note: Allen-derived claims are for non-commercial use with attribution and are not in the dumps. The maintainer chose this on 4 October 2026 over serving repository data only.

### Consequences

* Good, because clients get a stable, documented contract, with what they may do with each claim stated in the data.
* Good, because the API costs nothing extra to run and inherits the site's deployment and cache.
* Bad, because the contract is hand-written: a new field needs the schema, the shape and the test changed together (the contract tests catch a mismatch).
* Neutral: write access stays with pull requests; the API is read-only.
