import type { Metadata } from "next";

import { DataUnavailable } from "@/components/data-unavailable";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getAtlases, getRegions } from "@/lib/data";
import { citationParts, speciesName } from "@/lib/format";
import { AMYGDALA, amygdalaRegions } from "@/lib/regions";

export const revalidate = 300;
export const metadata: Metadata = { title: "Atlases" };

function uberonHref(curie: string): string {
  return `https://purl.obolibrary.org/obo/${curie.replace(":", "_")}`;
}

export default async function Atlases() {
  const [atlases, regions] = await Promise.all([getAtlases(), getRegions()]);
  if (atlases === null || regions === null) return <DataUnavailable />;
  const all = Object.values(regions);
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Atlases</h1>
        <p className="max-w-2xl text-muted-foreground">
          Claims name regions in these pinned atlas versions. Region names and hierarchies are read from{" "}
          <a href="https://brainglobe.info/" className="underline underline-offset-4">
            BrainGlobe
          </a>{" "}
          at build time, and each region is mapped to UBERON by UBERON&apos;s own published bridge.
        </p>
      </header>
      {atlases.map((atlas) => {
        const own = all.filter((r) => r.atlas === atlas.id);
        const amygdala = amygdalaRegions(own);
        const cite = atlas.citation ? citationParts(atlas.citation) : null;
        return (
          <Card key={atlas.id}>
            <CardHeader>
              <CardTitle>
                <h2>{atlas.name}</h2>
              </CardTitle>
              <CardDescription>
                {speciesName(atlas.species)} · version {atlas.version} · {own.length.toLocaleString("en")} regions
                {cite && (
                  <>
                    {" · Cite "}
                    {cite.href ? (
                      <a href={cite.href} className="underline underline-offset-4">
                        {cite.text}
                      </a>
                    ) : (
                      cite.text
                    )}
                  </>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {amygdala.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Region</TableHead>
                      <TableHead>Name in the atlas</TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead>UBERON</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {amygdala.map((region) => (
                      <TableRow key={region.id}>
                        <TableCell className="font-medium">{region.acronym}</TableCell>
                        <TableCell>{region.name}</TableCell>
                        <TableCell className="font-mono">{region.id}</TableCell>
                        <TableCell>
                          <a href={uberonHref(region.uberon!)} className="underline underline-offset-4">
                            {AMYGDALA.find((t) => t.uberon === region.uberon)?.label}
                          </a>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground">
                  This atlas doesn&apos;t delineate the amygdala&apos;s nuclei, so claims about this species name UBERON
                  terms instead of its regions.
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
