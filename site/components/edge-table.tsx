"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { edgeHref, predicateLabel, speciesName, withParam } from "@/lib/format";
import type { EdgeSummary } from "@/lib/types";

function Filter({ name, label, values, format }: { name: string; label: string; values: string[]; format: (v: string) => string }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <NativeSelect
        value={params.get(name) ?? ""}
        onChange={(event) => router.replace(withParam(pathname, params, name, event.target.value), { scroll: false })}
      >
        <NativeSelectOption value="">All</NativeSelectOption>
        {values.map((value) => (
          <NativeSelectOption key={value} value={value}>
            {format(value)}
          </NativeSelectOption>
        ))}
      </NativeSelect>
    </label>
  );
}

export function EdgeTable({ edges }: { edges: EdgeSummary[] }) {
  const params = useSearchParams();
  const species = params.get("species");
  const predicate = params.get("predicate");
  const shown = edges.filter((e) => (!species || e.species === species) && (!predicate || e.predicate === predicate));
  const distinct = (key: "species" | "predicate") => [...new Set(edges.map((e) => e[key]))].sort();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4">
        <Filter name="species" label="Species" values={distinct("species")} format={speciesName} />
        <Filter name="predicate" label="Connection" values={distinct("predicate")} format={predicateLabel} />
        <span className="ml-auto self-center text-sm text-muted-foreground">
          {shown.length} of {edges.length} connections
        </span>
      </div>
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
          </TableRow>
        </TableHeader>
        <TableBody>
          {shown.map((edge) => (
            <TableRow key={edge.id}>
              <TableCell className="font-mono">{edge.subject_id}</TableCell>
              <TableCell>
                <Link href={edgeHref(edge.id)} className="underline underline-offset-4">
                  {predicateLabel(edge.predicate)}
                </Link>
              </TableCell>
              <TableCell className="font-mono">{edge.object_id}</TableCell>
              <TableCell>{speciesName(edge.species)}</TableCell>
              <TableCell className="text-right tabular-nums">{edge.n_claims}</TableCell>
              <TableCell className="tabular-nums">
                {edge.n_present} / {edge.n_absent}
              </TableCell>
              <TableCell>{edge.strength ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
