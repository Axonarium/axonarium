---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint 3.3)
---

# The site's static fallback: a snapshot of the database, bundled with the deploy

## Context and Problem Statement

The plan's Tier 1 says the site keeps serving when the live API can't: "Supabase free projects pause after a week of inactivity … the site should keep serving the last release", and sprint 3.3 is done only when the explorer "falls back to static data". Until now every page and API route read Supabase. When a read failed, Next.js kept serving pages it had already rendered, but an unvisited page, every read-API request and a deploy's own build failed while the database was down. How does the site answer without the database?

## Considered Options

* A snapshot of the serving tables, written by the deploy's build and bundled with the site's server routes; each query falls back to it
* Static export of the whole site from the release dumps
* A scheduled job that keeps the free Supabase project from pausing

## Decision Outcome

Chosen option: "a snapshot of the serving tables, bundled with the deploy", because the database only changes when the deploy rebuilds it. The deploy loads the database and then builds the site in the same run, so a snapshot written by that build holds exactly what the database holds, and answers from it are the same answers.

* **Writing it:** `python -m build --snapshot FILE` writes every row the build loads into the database, as one JSON file (the build-time Allen claims and the atlases' regions included, unlike the dumps). The deploy passes it to the site job, which puts it at `site/snapshot/snapshot.json`, as it does the brain meshes (ADR 0011).
* **Shipping it:** `next.config.ts` traces it into every server route (`outputFileTracingIncludes`), so it is read from the function's own files. It is never in `public/`, never committed (`site/.gitignore`) and never in a release.
* **Answering from it:** each query in `site/lib/data.ts` asks Supabase first. If Supabase fails, or isn't configured, the same query is answered by `site/lib/offline.ts`, which applies the same filters, order and pages to the snapshot's rows. With neither, as in pull-request CI, pages still say the data isn't connected.
* **Allen terms:** the snapshot holds the same Allen-derived rows the live site and API already serve under the Allen terms (ADR 0005), at no new public address. Like the meshes, it passes between the deploy's two jobs as a workflow artifact kept for one day.

### Consequences

* Good, because a paused or unreachable Supabase no longer takes down any page or API route, and a deploy no longer fails when Supabase is down while the site is built.
* Good, because the fallback needs no new service, dependency or secret.
* Bad, because each query exists twice: as a Supabase query and as array code over the snapshot. `site/lib/offline.test.ts` pins the second's filters, order and pages, and a change to one must be made in the other.
* Neutral: the plan's alternative, keeping the free project awake, would hide the problem without removing it; a paid Supabase plan remains an open decision.

### Confirmation

`build/tests/test_snapshot.py` covers the snapshot's contents. `site/lib/offline.test.ts` covers every fallback query. By hand: a production build and server pointed at an unreachable Supabase URL answered pages and API requests from a snapshot.
