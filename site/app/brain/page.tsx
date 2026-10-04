import type { Metadata } from "next";
import Link from "next/link";

import { BrainView } from "@/components/brain/brain-view";
import { DataUnavailable } from "@/components/data-unavailable";
import { getBrainEdges } from "@/lib/data";

export const revalidate = 300;
export const metadata: Metadata = {
  title: "Brain",
  description: "The mouse amygdala's projections in 3D and as a network, from cited tracer experiments.",
};

const ATLAS = "allen-mouse-ccf-2017";

export default async function Brain() {
  const edges = await getBrainEdges(ATLAS);
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Where the mouse amygdala projects</h1>
        <p className="max-w-3xl text-muted-foreground">
          In 3D or as a network: where the amygdala sends its axons, from anterograde tracer injections in the Allen Mouse Brain Connectivity
          Atlas. Each arc is a connection made from cited claims; open one to see the experiments behind it. Region
          meshes: Allen Mouse Brain Common Coordinate Framework, via BrainGlobe.
        </p>
      </div>
      {edges === null ? (
        <DataUnavailable />
      ) : edges.length === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-muted-foreground">No mouse connections yet.</p>
      ) : (
        <BrainView edges={edges} base={`/brain/${ATLAS}`} />
      )}
      <p className="text-sm text-muted-foreground">
        Prefer a table? Every connection is on{" "}
        <Link href="/explore" className="underline underline-offset-4">
          Explore
        </Link>
        .
      </p>
    </div>
  );
}
