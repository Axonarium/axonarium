import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DataUnavailable } from "@/components/data-unavailable";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { BrainEdge } from "@/lib/brain";
import { getRegion } from "@/lib/data";
import { edgeFromParam, edgeHref, regionHref } from "@/lib/format";
import type { RegionName } from "@/lib/regions";

export const revalidate = 300;

// Rendered on first visit, then cached and revalidated like the other pages (incremental static regeneration).
export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: PageProps<"/regions/[id]">): Promise<Metadata> {
  return { title: edgeFromParam((await params).id) };
}

function Connections({ title, edges, end, names }: {
  title: string;
  edges: BrainEdge[];
  end: "source" | "target";
  names: Record<string, RegionName>;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">
        {title} <span className="text-base font-normal text-muted-foreground">({edges.length})</span>
      </h2>
      {edges.length === 0 ? (
        <p className="text-sm text-muted-foreground">None recorded yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Region</TableHead>
              <TableHead className="text-right">Strongest density</TableHead>
              <TableHead className="text-right">Claims (accepted)</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {edges.map((edge) => {
              const id = edge[end];
              const name = names[id];
              return (
                <TableRow key={edge.id}>
                  <TableCell className="whitespace-normal">
                    <Link href={regionHref(id)} className="font-medium underline-offset-4 hover:underline">
                      {name?.acronym ?? id}
                    </Link>{" "}
                    {name && <span className="text-muted-foreground">{name.name}</span>}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{edge.density?.toFixed(3) ?? "–"}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {edge.claims} ({edge.accepted})
                  </TableCell>
                  <TableCell className="text-right">
                    <Link href={edgeHref(edge.id)} className="underline underline-offset-4">
                      evidence
                    </Link>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </section>
  );
}

export default async function RegionPage({ params }: PageProps<"/regions/[id]">) {
  const found = await getRegion(edgeFromParam((await params).id));
  if (found === undefined) return <DataUnavailable />;
  if (found === null) notFound();
  const { region, children, outputs, inputs, names } = found;
  const parent = region.parent ? names[region.parent] : null;
  const drawn = region.atlas === "allen-mouse-ccf-2017" && outputs.length + inputs.length > 0;
  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <p className="text-sm text-muted-foreground">
          <Link href="/atlases" className="underline-offset-4 hover:underline">
            {region.atlas}
          </Link>{" "}
          · <span className="font-mono">{region.id}</span>
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          {region.acronym} <span className="font-normal text-muted-foreground">{region.name}</span>
        </h1>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {region.amygdala && <Badge>Amygdala</Badge>}
          {region.uberon && (
            <a
              href={`https://www.ebi.ac.uk/ols4/ontologies/uberon/classes/${encodeURIComponent(encodeURIComponent(`http://purl.obolibrary.org/obo/${region.uberon.replace(":", "_")}`))}`}
              className="underline underline-offset-4"
            >
              {region.uberon}
              {region.uberon_label && ` (${region.uberon_label})`}
            </a>
          )}
          {parent && region.parent && (
            <span>
              Part of{" "}
              <Link href={regionHref(region.parent)} className="underline underline-offset-4">
                {parent.acronym} {parent.name}
              </Link>
            </span>
          )}
          {drawn && (
            <Link href={`/brain?region=${encodeURIComponent(region.id)}`} className="underline underline-offset-4">
              See it on the brain
            </Link>
          )}
        </div>
        {children.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Subregions:{" "}
            {children.map((child, i) => (
              <span key={child.id}>
                {i > 0 && ", "}
                <Link href={regionHref(child.id)} className="underline-offset-4 hover:underline" title={child.name}>
                  {child.acronym ?? child.name}
                </Link>
              </span>
            ))}
          </p>
        )}
      </header>
      <Connections title="Projects to" edges={outputs} end="target" names={names} />
      <Connections title="Receives from" edges={inputs} end="source" names={names} />
    </div>
  );
}
