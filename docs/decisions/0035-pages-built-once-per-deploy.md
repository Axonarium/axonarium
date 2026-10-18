---
status: proposed
date: 2026-10-18
decision-makers: Tyler Banks
consulted: Claude
---

# Pages built once per deploy, or rendered on request, never revalidated on a timer

## Context and Problem Statement

In October 2026 Vercel reported the site's ISR writes at 206,000 against the Hobby plan's 200,000 a month. Every data page exported `revalidate = 300` (sprint 3.3a, when the database was still empty), and claim, connection and region pages were cached on first visit (`generateStaticParams` returning nothing). Three facts make that costly:

* **The database only changes when a deploy rebuilds it.** Only the Deploy workflow writes it, right before it deploys the site with a snapshot of the same rows (ADR 0017). A page revalidated between deploys can never show anything new.
* **Each deploy starts with an empty ISR cache.** Vercel scopes the cache to a deployment, so after every deploy each page is rendered and written again on its first visit. Main deployed 104 times between 4 and 16 October 2026.
* **There are tens of thousands of pages, and crawlers find them.** The deploy of 16 October held 17,477 claims and 6,307 connections across 1,064 atlas regions; the sitemap lists every connection and connected region, and connection pages link every claim. A claim or connection page is about 55 KB uncompressed across its HTML and React payloads, a few 8 KB write units once Vercel compresses it, and the home page and `/brain`, which carry every mouse connection, are many times that.

How should pages be cached when their data is fixed for the life of a deployment?

## Considered Options

* Build the pages everyone shares once per deploy; render claim, connection and region pages on request, uncached
* Keep caching every page on first visit, but never revalidate (`revalidate = false`)
* Prerender every page in the deploy's build
* Cache claim, connection and region pages at Vercel's CDN with `Vercel-CDN-Cache-Control`
* Move to a paid Vercel plan

## Decision Outcome

Chosen option: "build the shared pages once per deploy; render the rest on request", because it ends ISR writes at runtime without serving anything staler than today.

* **Shared pages:** the home page, `/brain`, `/brain/rat`, `/regions`, `/atlases`, the sitemap and the link preview drop `revalidate`. The deploy's build renders them from the database it has just loaded, and they are served as built until the next deploy.
* **Long-tail pages:** `/claims/[id]`, `/edges/[id]` and `/regions/[id]` drop `revalidate` and `generateStaticParams`, so Next.js renders them for each request, as `/explore` and `/sources/[id]` already are (ADR 0025).
* **Links to long-tail pages don't prefetch** (`prefetch={false}`, as the explore table's links already did). A page rendered on request would run a function for every link that scrolls into view, and the brain viewer's links, whose connection IDs weren't URL-encoded, kept re-requesting theirs until the browser never went idle.
* The read API keeps its five-minute edge cache (ADR 0013); edge caching is not ISR.

### Consequences

* Good, because nothing writes to the ISR cache at runtime: the only cached pages are the build's own.
* Good, because the shared pages no longer re-query every connection and claim every five minutes they are visited.
* Bad, because every view of a claim, connection or region page runs a function and a few small Supabase queries, where a repeat view was served from the cache. Most of those views come from crawlers on pages no one else opened in that deployment, which were rendered anyway. Hobby includes a million function invocations a month.
* Neutral: when neither Supabase nor the snapshot can answer, a long-tail page shows `app/error.tsx` instead of an older cached copy. Production always has the snapshot.

### Confirmation

`next build` lists the shared pages as static with no revalidate time, and `/claims/[id]`, `/edges/[id]` and `/regions/[id]` as dynamic. Opening `/brain` requests no connection page until a link is clicked. After a deploy, Vercel's usage page shows ISR writes flat between deploys.

## Pros and Cons of the Options

### Keep caching every page on first visit, but never revalidate

* Good, because repeat views stay cached.
* Bad, because every page visited is still written once per deployment, about 25,000 pages times the deploy count at worst.

### Prerender every page in the deploy's build

* Bad, because the build would render about 25,000 pages on every deploy, and the plan's growth multiplies that.

### Cache long-tail pages at Vercel's CDN

* Good, because repeat views stay cached without ISR.
* Bad, because it needs headers Next.js doesn't manage on dynamic pages, and a shared cache must keep the HTML and React payload of one URL apart.

### Move to a paid Vercel plan

* Bad, because it pays for regenerating pages that cannot change. It remains open if traffic outgrows Hobby's other limits.
