import type { Metadata } from "next";
import Link from "next/link";

import { BrainView } from "@/components/brain/brain-view";
import { DataUnavailable } from "@/components/data-unavailable";
import { namedRegions } from "@/lib/brain";
import { getModules, getNames, getSpeciesEdges } from "@/lib/data";

export const revalidate = 300;
export const metadata: Metadata = {
  title: "Rat brain",
  description:
    "The rat amygdala's, hippocampal formation's and prefrontal cortex's outputs and inputs in 3D and as a network, from cited papers.",
};

const RAT = "NCBITaxon:10116";
const ATLAS = "waxholm-sd-rat-v4";

// Rat claims name UBERON terms, which the 3D view draws on the Waxholm structures that hold them (build/waxholm.py;
// ADR 0034).
export default async function RatBrain() {
  const [edges, modules] = await Promise.all([getSpeciesEdges(RAT), getModules()]);
  const ids = [...new Set((edges ?? []).flatMap((e) => [e.source, e.target]))];
  const names = await getNames(ids);
  const regions = namedRegions(ids, names, (modules ?? []).map((m) => ({ id: m.id, terms: m.terms ?? [] })));
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">The rat brain&apos;s connections</h1>
        <p className="max-w-3xl text-muted-foreground">
          In 3D or as a network, one circuit at a time: where it sends its axons, and which regions send axons to it, from
          rat experiments in published papers. Each link is a connection made from cited claims; open one to see the
          evidence behind it. Regions are UBERON terms, as the papers&apos; claims name them. Region meshes: Waxholm Space
          atlas of the Sprague Dawley rat brain, version 4 (
          <a href="https://doi.org/10.1038/s41592-023-02034-3" className="underline underline-offset-4">
            Kleven et al. 2023
          </a>
          ), via BrainGlobe, under{" "}
          <a href="https://creativecommons.org/licenses/by-sa/4.0/" className="underline underline-offset-4">
            CC BY-SA 4.0
          </a>
          .
        </p>
      </div>
      {edges === null ? (
        <DataUnavailable />
      ) : edges.length === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-muted-foreground">No rat connections yet.</p>
      ) : (
        <BrainView
          edges={edges}
          base={`/brain/${ATLAS}`}
          regions={regions}
          modules={modules?.map(({ id, name }) => ({ id, name }))}
          species="rat"
        />
      )}
      <p className="text-sm text-muted-foreground">
        Prefer a table? Every rat connection is on{" "}
        <Link href={`/explore?species=${encodeURIComponent(RAT)}`} className="underline underline-offset-4">
          Explore
        </Link>
        .
      </p>
    </div>
  );
}
