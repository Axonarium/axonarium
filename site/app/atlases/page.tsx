import type { Metadata } from "next";
import Link from "next/link";

import { DataUnavailable } from "@/components/data-unavailable";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getAtlases } from "@/lib/data";
import { citationParts, regionHref, speciesName } from "@/lib/format";

export const revalidate = 300;
export const metadata: Metadata = { title: "Atlases" };

function uberonHref(curie: string): string {
  return `https://purl.obolibrary.org/obo/${curie.replace(":", "_")}`;
}

export default async function Atlases() {
  const atlases = await getAtlases();
  if (atlases === null) return <DataUnavailable />;
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Atlases</h1>
        <p className="max-w-2xl text-muted-foreground">
          Claims name regions in these pinned atlas versions. Region names and hierarchies are read from{" "}
          <a href="https://brainglobe.info/" className="underline underline-offset-4">
            BrainGlobe
          </a>{" "}
          at build time; each region is mapped to UBERON by UBERON&apos;s own published bridge, and UBERON&apos;s hierarchy decides which belong to the amygdala.
        </p>
      </header>
      {atlases.map(({ atlas, regions, amygdala }) => {
        const cite = atlas.citation ? citationParts(atlas.citation) : null;
        return (
          <Card key={atlas.id}>
            <CardHeader>
              <CardTitle>
                <h2>{atlas.name}</h2>
              </CardTitle>
              <CardDescription>
                {speciesName(atlas.species)} · version {atlas.version}
                {regions > 0 && ` · ${regions.toLocaleString("en")} regions`}
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
                        <TableCell className="font-medium">
                          <Link href={regionHref(region.id)} className="underline-offset-4 hover:underline">
                            {region.acronym}
                          </Link>
                        </TableCell>
                        <TableCell>{region.name}</TableCell>
                        <TableCell className="font-mono">{region.id}</TableCell>
                        <TableCell>
                          <a href={uberonHref(region.uberon!)} className="underline underline-offset-4">
                            {region.uberon_label ?? region.uberon}
                          </a>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : regions > 0 ? (
                <p className="text-sm text-muted-foreground">No region of this atlas maps to the amygdala in UBERON.</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No regions of this atlas are loaded: it doesn&apos;t delineate the amygdala&apos;s nuclei, so claims
                  about this species name UBERON terms instead.
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
