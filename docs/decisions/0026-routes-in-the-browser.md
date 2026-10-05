---
status: accepted
date: 2026-10-05
decision-makers: Tyler Banks
consulted: Claude (sprint 3.5)
---

# The path finder runs in the browser

## Context and Problem Statement

The plan's explorer has a path finder: "pick a start and end; the route animates hop by hop, each hop opening its citations" (Part 1, "Explorer"). Its architecture also says graph analytics, paths among them, "are precomputed in Python and stored as tables, since Postgres is not a graph engine". Sprint 3.5 builds the path finder. Where are routes found, and which route is "the" route between two regions?

## Considered Options

* In the browser, over the connections the brain page already loads
* A table of every pair's shortest route, precomputed by the build
* A route endpoint in the read API, computed per request

## Decision Outcome

Chosen option: "in the browser". The brain page already holds every connection it can draw: about a thousand, among about three hundred regions. A breadth-first search over them takes well under a millisecond. Precomputing would store a row for each of about 90,000 ordered pairs, most never asked for, and rebuild them on every merge. An endpoint would make each route a round trip, and the page would still need the connections to draw them.

* **The route:** the fewest hops along connections, in their direction. Among routes with as few hops, the one whose weakest hop has the highest projection density; a hop that states no density counts as 0. Remaining ties go to the first by connection ID, so a route is the same every time.
  * Hop count is method-neutral. Densities from different experiments and methods aren't probabilities that could be multiplied into a "most likely" route.
  * The weakest-hop tie-break prefers the route best supported where it is thinnest.
* **What it runs over:** every connection the brain viewer can draw, outputs and inputs alike, whatever the minimum density. Connections whose every claim is proposed are included and drawn dashed, as everywhere in the viewer.
* **Each hop's citations** come from the read API (`/api/v1/connections/{id}`) as the hop appears: each distinct source, how many of the hop's claims cite it, and their evidence classes. A link opens the connection's evidence page.
* **Shareable:** the route's ends are in the URL (`/brain?from=…&to=…`). Those who ask their browser for less motion get the whole route at once.

### Consequences

* Good, because routes need no new table, build step or endpoint, and answer instantly.
* Good, because the route rule is simple to state on the page and to check by hand.
* Bad, because the read API and the MCP server can't answer route questions yet. When they need to, or when graphs outgrow what a page can load (neuron types, more species), routes move to Python as the plan describes. `lib/route.ts` is then the reference for the same rule.
* Neutral: routes run only through connections in the brain viewer's atlas, so far the Allen mouse atlas.
