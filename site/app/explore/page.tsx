import type { Metadata } from "next";

import { DataUnavailable } from "@/components/data-unavailable";
import { EdgeTable } from "@/components/edge-table";
import { ExploreFilters } from "@/components/explore-filters";
import { Pager } from "@/components/pager";
import { getEdgeFacets, getNames, listConnections } from "@/lib/data";
import { exploreHref, exploreState, PAGE_SIZE, pageCount } from "@/lib/explore";
import { regionLabel } from "@/lib/regions";

export const metadata: Metadata = { title: "Explore" };

// A page of connections at a time, filtered and paged on the server from the URL (lib/explore.ts): a thousand rows at
// once took a mid-range phone seconds to lay out and hydrate (ADR 0025).
export default async function Explore({ searchParams }: PageProps<"/explore">) {
  const facets = await getEdgeFacets();
  const state = facets && exploreState(await searchParams, facets);
  const found =
    state &&
    (await listConnections({
      species: state.species || null,
      predicate: state.predicate || null,
      limit: PAGE_SIZE,
      offset: (state.page - 1) * PAGE_SIZE,
    }));
  const ids = [...new Set((found?.items ?? []).flatMap((e) => [e.subject_id, e.object_id]))];
  const regions = await getNames(ids);
  const labels = Object.fromEntries(ids.map((id) => [id, regionLabel(id, regions)]));
  const pages = found ? pageCount(found.total) : 1;
  const first = state ? (state.page - 1) * PAGE_SIZE : 0;
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Connections</h1>
        <p className="max-w-2xl text-muted-foreground">
          Each row is computed from cited claims, strongest projection density first. Open a connection to see every claim behind it, with its source.
        </p>
      </div>
      {!facets || !state || !found ? (
        <DataUnavailable />
      ) : facets.species.length === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-muted-foreground">
          No connections yet. The first ones arrive with the atlas and connectivity sprints; this page fills in as
          claims are merged.
        </p>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <ExploreFilters facets={facets} chosen={state} />
            <p className="ml-auto text-sm text-muted-foreground">
              {found.total === 0
                ? "No connections match"
                : `${(first + 1).toLocaleString("en")}–${Math.min(first + PAGE_SIZE, found.total).toLocaleString("en")} of ${found.total.toLocaleString("en")} connections`}
            </p>
          </div>
          <EdgeTable edges={found.items} labels={labels} />
          <Pager page={state.page} pages={pages} href={(n) => exploreHref({ ...state, page: n })} previous="← Stronger" next="Weaker →" />
        </div>
      )}
    </div>
  );
}
