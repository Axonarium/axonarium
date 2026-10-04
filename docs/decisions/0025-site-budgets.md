---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint 3.5)
---

# The site's accessibility and performance budgets

## Context and Problem Statement

The plan sets the explorer's bar as "smooth interaction on a mid-range phone, tested in CI with a performance budget". It also says every 3D view has a 2D and table equivalent, partly for accessibility (Part 1, "Explorer"). Sprint 3.5 is done when the maintainer approves the look and "accessibility and performance budgets pass in CI". How are the budgets measured, on what data, and what are they?

## Considered Options

* axe-core through Playwright for accessibility, and Lighthouse CI for performance, on a production build of real data
* Lighthouse alone, for both
* Checks against the pull request's build as it is (no data: every page shows "data unavailable")

## Decision Outcome

Chosen option: "axe-core through Playwright, and Lighthouse CI, on real data". Both are the standard open tools for these jobs (axe-core: MPL-2.0; Lighthouse and Lighthouse CI: Apache-2.0). axe checks every page at phone and desktop sizes and names each failing element. Lighthouse adds the timings a phone feels. Without data the pages would be empty, and their budgets meaningless.

* **Data:** the `budgets` job rebuilds the snapshot and meshes from the checks job's cache, as the deploy does (ADR 0017, ADR 0011). It builds the site against them. Supabase's URL points nowhere, so every page answers from the snapshot. Cloudflare's test keys open the evidence form (ADR 0024), so its accessibility is checked too.
* **Accessibility** (`site/e2e/`, `npm run e2e`):
  * axe-core's WCAG 2.1 A and AA rules, with no violation allowed;
  * one page of each kind (home, brain, explore, regions, a region, a claim, a connection, atlases, about, not found) and the open evidence form;
  * on a phone (Pixel 7) and a desktop;
  * any uncaught error or 5xx response while a page loads also fails.
* **Performance** (`site/lighthouserc.cjs`):
  * Lighthouse's default mobile emulation: a mid-range phone with a 4× slower CPU on a slow 4G connection;
  * three runs per page, judged on the median run;
  * Lighthouse's own accessibility score must be 100.

  | Pages | Performance score | Largest paint | Blocking time | Layout shift | Weight |
  | --- | --- | --- | --- | --- | --- |
  | Text and tables (explore, regions, a region, a claim, a connection) | ≥ 0.9 | ≤ 2.5 s | ≤ 200 ms | ≤ 0.1 | ≤ 1 MB |
  | With the 3D brain (home's preview, `/brain`) | none | ≤ 4 s | ≤ 600 ms | ≤ 0.1 | ≤ 6 MB |

  The first group uses Web Vitals' "good" thresholds. three.js and the meshes are heavy by nature, so the 3D pages' budget keeps them stable while they load and stops them growing.
* **Lighthouse CI runs through `npx` at a pinned version**, as the deploy runs the Vercel CLI. It isn't a dependency: its Puppeteer chain carries advisories (in its browser downloader and FTP client, which it never uses here) that would sit in the lockfile.
* **Reports** (Lighthouse's, and Playwright's on failure) are kept for seven days as the run's `budgets` artifact.

### Consequences

* Good, because any change that breaks accessibility, slows a page or makes it jump fails its pull request, with the offending element or metric named.
* Good, because the first run found two layout shifts, now fixed. The brain viewer's placeholder didn't match the home page's smaller preview. The "no meshes" notice collapsed the brain page.
* Bad, because the job takes several minutes: a rebuild, a site build, about 40 browser runs.
* Bad, because lab numbers vary between CI machines. Medians of three runs and budgets with some margin keep the noise down; a budget that flakes is raised in a reviewed change, never silently.
* Neutral: the home page's 3D preview costs a phone about 0.3–0.5 s of blocking time at load. Whether phones get a lighter preview is a design question for the maintainer's look review (sprint 3.5).
