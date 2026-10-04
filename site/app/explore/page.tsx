import type { Metadata } from "next";
import Link from "next/link";

import { DataUnavailable } from "@/components/data-unavailable";
import { EdgeTable } from "@/components/edge-table";
import { ExploreFilters } from "@/components/explore-filters";
import { getEdgeFacets, getRegionNames, listConnections } from "@/lib/data";
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
  const regions = await getRegionNames(ids);
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
          {pages > 1 && (
            <nav aria-label="Pages" className="flex items-center justify-between gap-4 text-sm">
              {state.page > 1 ? (
                <Link href={exploreHref({ ...state, page: state.page - 1 })} className="underline underline-offset-4">
                  ← Stronger
                </Link>
              ) : (
                <span />
              )}
              <span className="text-muted-foreground">
                Page {state.page} of {pages}
              </span>
              {state.page < pages ? (
                <Link href={exploreHref({ ...state, page: state.page + 1 })} className="underline underline-offset-4">
                  Weaker →
                </Link>
              ) : (
                <span />
              )}
            </nav>
          )}
        </div>
      )}
    </div>
  );
}
