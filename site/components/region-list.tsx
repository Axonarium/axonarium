"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { regionHref } from "@/lib/format";
import type { IndexedRegion } from "@/lib/region-index";

export function RegionList({ regions }: { regions: IndexedRegion[] }) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const shown = q
    ? regions.filter((r) => r.name.toLowerCase().includes(q) || (r.acronym ?? "").toLowerCase().includes(q) || r.id.toLowerCase() === q)
    : regions;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter by name or acronym, such as BLA or thalamus"
          aria-label="Filter regions"
          className="h-9 w-full max-w-sm rounded-lg border border-input bg-transparent px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
        <span className="ml-auto text-sm text-muted-foreground">
          {shown.length} of {regions.length} regions
        </span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Region</TableHead>
            <TableHead className="text-right">Projects to</TableHead>
            <TableHead className="text-right">Receives from</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {shown.map((region) => (
            <TableRow key={region.id}>
              <TableCell className="whitespace-normal">
                <Link href={regionHref(region.id)} className="font-medium underline-offset-4 hover:underline">
                  {region.acronym ?? region.id}
                </Link>{" "}
                <span className="text-muted-foreground">{region.name}</span>{" "}
                {region.amygdala && <Badge variant="secondary">Amygdala</Badge>}
              </TableCell>
              <TableCell className="text-right tabular-nums">{region.outputs}</TableCell>
              <TableCell className="text-right tabular-nums">{region.inputs}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
