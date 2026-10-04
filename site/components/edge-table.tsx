// The explore page's table: one page of connections, strongest projection density first, rendered on the server.

import Link from "next/link";

import { RegionName } from "@/components/region-name";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { edgeHref, predicateLabel, speciesName } from "@/lib/format";
import type { Label } from "@/lib/regions";
import type { EdgeSummary } from "@/lib/types";

export function EdgeTable({ edges, labels }: { edges: EdgeSummary[]; labels: Record<string, Label> }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>From</TableHead>
          <TableHead>Connection</TableHead>
          <TableHead>To</TableHead>
          <TableHead>Species</TableHead>
          <TableHead className="text-right">Claims</TableHead>
          <TableHead>Found / tested absent</TableHead>
          <TableHead>Strength</TableHead>
          <TableHead className="text-right">Density</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {edges.map((edge) => (
          <TableRow key={edge.id}>
            <TableCell>
              <RegionName label={labels[edge.subject_id]} />
            </TableCell>
            <TableCell>
              <Link href={edgeHref(edge.id)} prefetch={false} className="underline underline-offset-4">
                {predicateLabel(edge.predicate)}
              </Link>
            </TableCell>
            <TableCell>
              <RegionName label={labels[edge.object_id]} />
            </TableCell>
            <TableCell>{speciesName(edge.species)}</TableCell>
            <TableCell className="text-right tabular-nums">{edge.n_claims}</TableCell>
            <TableCell className="tabular-nums">
              {edge.n_present} / {edge.n_absent}
            </TableCell>
            <TableCell>{edge.strength ?? "—"}</TableCell>
            <TableCell className="text-right tabular-nums">{edge.density?.toFixed(3) ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
