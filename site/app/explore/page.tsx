import type { Metadata } from "next";
import { Suspense } from "react";

import { DataUnavailable } from "@/components/data-unavailable";
import { EdgeTable } from "@/components/edge-table";
import { listEdges } from "@/lib/data";

export const revalidate = 300;
export const metadata: Metadata = { title: "Explore" };

export default async function Explore() {
  const edges = await listEdges();
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Connections</h1>
        <p className="max-w-2xl text-muted-foreground">
          Each row is computed from cited claims. Open a connection to see every claim behind it, with its source.
        </p>
      </div>
      {!edges.ok ? (
        <DataUnavailable reason={edges.reason} />
      ) : edges.data.length === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-muted-foreground">
          No connections yet. The first ones arrive with the atlas and connectivity sprints; this page fills in as
          claims are merged.
        </p>
      ) : (
        <Suspense>
          <EdgeTable edges={edges.data} />
        </Suspense>
      )}
    </div>
  );
}
