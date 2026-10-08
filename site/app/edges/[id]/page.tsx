import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ClaimCard } from "@/components/claim-card";
import { DataUnavailable } from "@/components/data-unavailable";
import { RegionName } from "@/components/region-name";
import { getClaims, getEdge, getNames } from "@/lib/data";
import { regionLabel } from "@/lib/regions";
import { edgeFromParam, predicateLabel, speciesName } from "@/lib/format";

export const revalidate = 300;

// Rendered on first visit, then cached and revalidated like the other pages (incremental static regeneration).
export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: PageProps<"/edges/[id]">): Promise<Metadata> {
  const [subject, predicate, object] = edgeFromParam((await params).id).split("|");
  return { title: `${subject} ${predicateLabel(predicate ?? "")} ${object}` };
}

export default async function EdgePage({ params }: PageProps<"/edges/[id]">) {
  const e = await getEdge(edgeFromParam((await params).id));
  if (e === undefined) return <DataUnavailable />;
  if (e === null) notFound();
  const [claims, regions] = await Promise.all([getClaims(e.claim_ids), getNames([e.subject_id, e.object_id])]);
  const sources = new Set(claims.map((c) => c.source_key)).size;
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-sm text-muted-foreground">{speciesName(e.species)}</p>
        <h1 className="text-3xl font-semibold tracking-tight">
          <RegionName heading label={regionLabel(e.subject_id, regions)} /> {predicateLabel(e.predicate)}{" "}
          <RegionName heading label={regionLabel(e.object_id, regions)} />
        </h1>
        <p className="text-muted-foreground">
          {e.n_claims} claim{e.n_claims === 1 ? "" : "s"} from {sources} source{sources === 1 ? "" : "s"}: {e.n_present} found,{" "}
          {e.n_absent} tested and absent,{" "}
          {e.n_ambiguous} ambiguous{e.n_disputed ? `, ${e.n_disputed} disputed` : ""}. Evidence:{" "}
          {e.evidence_classes.map((c) => c.replaceAll("_", " ")).join(", ")}.
          {e.strength && ` Strongest reported: ${e.strength}.`}
          {e.density !== null && ` Strongest projection density: ${e.density.toFixed(3)}.`}
        </p>
      </header>
      <section aria-labelledby="claims" className="space-y-3">
        <h2 id="claims" className="text-xl font-semibold">
          The claims behind it
        </h2>
        {claims.map((claim) => (
          <ClaimCard key={claim.id} claim={claim} />
        ))}
      </section>
    </div>
  );
}
