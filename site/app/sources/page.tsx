import type { Metadata } from "next";
import Link from "next/link";

import { DataUnavailable } from "@/components/data-unavailable";
import { Pager } from "@/components/pager";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listSources } from "@/lib/data";
import { pageParam, sourceHref } from "@/lib/format";

export const metadata: Metadata = { title: "Sources" };

const PAGE_SIZE = 100;

// Every paper and dataset the claims cite, those with the most claims first, a page at a time on the server.
export default async function Sources({ searchParams }: PageProps<"/sources">) {
  const page = pageParam((await searchParams).page);
  const found = await listSources(PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const pages = found ? Math.max(1, Math.ceil(found.total / PAGE_SIZE)) : 1;
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Sources</h1>
        <p className="max-w-2xl text-muted-foreground">
          The papers and datasets the claims cite, those with the most claims first. Open one to see every claim drawn
          from it.
        </p>
      </div>
      {!found ? (
        <DataUnavailable />
      ) : found.total === 0 ? (
        <p className="rounded-lg border border-dashed p-6 text-muted-foreground">No sources yet.</p>
      ) : (
        <div className="space-y-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Source</TableHead>
                <TableHead>Journal</TableHead>
                <TableHead className="text-right">Year</TableHead>
                <TableHead className="text-right">Claims</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {found.items.map((source) => (
                <TableRow key={source.id}>
                  <TableCell className="max-w-xl whitespace-normal">
                    <Link href={sourceHref(source.id)} prefetch={false} className="underline underline-offset-4">
                      {source.title ?? source.id}
                    </Link>
                    {source.retracted && <span className="ml-2 text-sm font-medium text-destructive">retracted</span>}
                  </TableCell>
                  <TableCell className="whitespace-normal text-muted-foreground">{source.journal ?? "—"}</TableCell>
                  <TableCell className="text-right tabular-nums">{source.year ?? "—"}</TableCell>
                  <TableCell className="text-right tabular-nums">{source.n_claims?.toLocaleString("en") ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pager page={page} pages={pages} href={(n) => (n > 1 ? `/sources?page=${n}` : "/sources")} />
        </div>
      )}
    </div>
  );
}
