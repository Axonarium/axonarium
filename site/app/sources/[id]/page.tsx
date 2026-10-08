import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Citation } from "@/components/citation";
import { ClaimCard } from "@/components/claim-card";
import { DataUnavailable } from "@/components/data-unavailable";
import { Pager } from "@/components/pager";
import { RegionName } from "@/components/region-name";
import { getNames, getSource, listSourceClaims } from "@/lib/data";
import { citedAs, edgeFromParam, pageParam, predicateLabel, sourceHref, speciesName } from "@/lib/format";
import { regionLabel } from "@/lib/regions";

const PAGE_SIZE = 50;

// Rendered on demand, like the explore page: its claims are paged by the URL's ?page=.

export async function generateMetadata({ params }: PageProps<"/sources/[id]">): Promise<Metadata> {
  const source = await getSource(edgeFromParam((await params).id));
  return { title: source?.title ?? "Source" };
}

const KINDS: Record<string, string> = { journal_article: "Journal article", preprint: "Preprint", dataset: "Dataset" };

export default async function SourcePage({ params, searchParams }: PageProps<"/sources/[id]">) {
  const id = edgeFromParam((await params).id);
  const page = pageParam((await searchParams).page);
  const [source, found] = await Promise.all([getSource(id), listSourceClaims(id, PAGE_SIZE, (page - 1) * PAGE_SIZE)]);
  if (found === null) return <DataUnavailable />;
  if (source === null) notFound();
  const names = await getNames([...new Set(found.items.flatMap((c) => [c.subject_id, c.object_id]))]);
  const pages = Math.max(1, Math.ceil(found.total / PAGE_SIZE));
  const identifiers = found.items[0] ?? citedAs(source.id);
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <p className="text-sm text-muted-foreground">{KINDS[source.kind] ?? "Source"}</p>
        <h1 className="text-3xl font-semibold tracking-tight">{source.title ?? source.id}</h1>
        {(source.journal || source.year) && (
          <p className="text-muted-foreground">{[source.journal, source.year].filter(Boolean).join(", ")}</p>
        )}
        <Citation cited={identifiers} />
        {source.kind === "preprint" && (
          <p className="text-sm text-muted-foreground">A preprint: not yet peer reviewed, so weaker evidence than a published paper.</p>
        )}
        {source.retracted && <p className="text-sm font-medium text-destructive">This paper has been retracted, and so have its claims.</p>}
        {source.license && <p className="text-sm text-muted-foreground">Licence: {source.license}</p>}
      </header>
      <section aria-labelledby="claims" className="space-y-3">
        <h2 id="claims" className="text-xl font-semibold">
          {found.total.toLocaleString("en")} claim{found.total === 1 ? "" : "s"} from this source
        </h2>
        {found.items.map((claim) => (
          <ClaimCard
            key={claim.id}
            claim={claim}
            cited={false}
            connection={
              <>
                <RegionName label={regionLabel(claim.subject_id, names)} /> {predicateLabel(claim.predicate)}{" "}
                <RegionName label={regionLabel(claim.object_id, names)} />
                <span className="font-normal text-muted-foreground"> · {speciesName(claim.species)}</span>
              </>
            }
          />
        ))}
        <Pager page={page} pages={pages} href={(n) => (n > 1 ? `${sourceHref(id)}?page=${n}` : sourceHref(id))} />
      </section>
    </div>
  );
}
