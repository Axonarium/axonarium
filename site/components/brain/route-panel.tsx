"use client";

// The path finder's panel (lib/route.ts): pick a start and an end. The route's hops appear one at a time, in the view
// and here, each opening the citations behind it.

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import type { BrainEdge, BrainRegion } from "@/lib/brain";
import { citationLinks, type Cited, edgeHref } from "@/lib/format";

export const ROUTE_COLOR = "#fde047";

interface HopClaim {
  evidence_class: string;
  citation: Cited;
}

/** A hop's distinct citations, from the read API, each with how many of the hop's claims cite it. */
function HopEvidence({ id }: { id: string }) {
  const [claims, setClaims] = useState<HopClaim[] | "failed" | null>(null);
  useEffect(() => {
    let live = true;
    fetch(`/api/v1/connections/${encodeURIComponent(id)}`)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`))))
      .then(
        (body: { claims_detail: HopClaim[] }) => live && setClaims(body.claims_detail),
        () => live && setClaims("failed"),
      );
    return () => void (live = false);
  }, [id]);

  if (claims === null) return <p className="text-xs text-muted-foreground">Loading its citations…</p>;
  if (claims === "failed") return <p className="text-xs text-muted-foreground">Its citations didn&apos;t load; the evidence page has them.</p>;
  const cited = new Map<string, { cited: Cited; claims: number; classes: Set<string> }>();
  for (const claim of claims) {
    const key = JSON.stringify([claim.citation.doi, claim.citation.pmid, claim.citation.pmcid, claim.citation.arxiv]);
    const entry = cited.get(key) ?? { cited: claim.citation, claims: 0, classes: new Set<string>() };
    entry.claims += 1;
    entry.classes.add(claim.evidence_class.replaceAll("_", " "));
    cited.set(key, entry);
  }
  return (
    <ul className="space-y-0.5 text-xs">
      {[...cited.values()].map(({ cited: source, claims: n, classes }) => (
        <li key={citationLinks(source)[0]?.href ?? "uncited"} className="text-muted-foreground">
          {citationLinks(source).map((link, i) => (
            <span key={link.href}>
              {i > 0 && " · "}
              <a href={link.href} className="underline underline-offset-4 hover:text-foreground">
                {link.label}
              </a>
            </span>
          ))}
          {`: ${n} claim${n === 1 ? "" : "s"}, ${[...classes].join(", ")}`}
        </li>
      ))}
    </ul>
  );
}

export function RoutePanel({ regions, starts, ends, from, to, hops, revealed, onFrom, onTo, onReplay, onClear }: {
  regions: Record<string, BrainRegion>;
  /** Regions a route can start from, and those it can reach from `from`. */
  starts: string[];
  ends: string[];
  from: string;
  to: string;
  hops: BrainEdge[] | null;
  /** How many of the hops are shown so far. */
  revealed: number;
  onFrom: (id: string) => void;
  onTo: (id: string) => void;
  onReplay: () => void;
  onClear: () => void;
}) {
  const option = (id: string) => (
    <NativeSelectOption key={id} value={id}>
      {regions[id].acronym} · {regions[id].name}
    </NativeSelectOption>
  );
  const current = hops && revealed > 0 ? hops[revealed - 1] : null;
  return (
    <div className="space-y-2">
      <h2 className="font-medium">Route</h2>
      <div className="grid grid-cols-[auto_1fr] items-center gap-x-2 gap-y-1.5">
        <label htmlFor="route-from" className="text-muted-foreground">
          From
        </label>
        <NativeSelect id="route-from" size="sm" className="w-full" value={from} onChange={(event) => onFrom(event.target.value)}>
          <NativeSelectOption value="">Choose a region</NativeSelectOption>
          {starts.map(option)}
        </NativeSelect>
        <label htmlFor="route-to" className="text-muted-foreground">
          To
        </label>
        <NativeSelect id="route-to" size="sm" className="w-full" value={to} disabled={!from} onChange={(event) => onTo(event.target.value)}>
          <NativeSelectOption value="">{from ? `${ends.length} regions reachable` : "Choose a start first"}</NativeSelectOption>
          {ends.map(option)}
        </NativeSelect>
      </div>
      {hops && (
        <>
          <p role="status" className="text-xs text-muted-foreground">
            {current
              ? `Hop ${revealed} of ${hops.length}: ${regions[current.source].acronym} → ${regions[current.target].acronym}`
              : `${hops.length} hop${hops.length === 1 ? "" : "s"}, the fewest there are`}
          </p>
          <ol className="max-h-[38vh] space-y-2 overflow-y-auto pr-1">
            {hops.slice(0, revealed).map((hop, i) => (
              <li key={hop.id} className="space-y-1 rounded-md border px-2.5 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="size-2 shrink-0 rounded-full" style={{ background: ROUTE_COLOR }} />
                  <span className="min-w-0 flex-1 truncate" title={`${regions[hop.source].name} → ${regions[hop.target].name}`}>
                    {i + 1}. {regions[hop.source].acronym} → <span className="font-medium">{regions[hop.target].acronym}</span>
                  </span>
                  <span className="tabular-nums text-muted-foreground">{hop.density?.toFixed(3) ?? "–"}</span>
                  <Link href={edgeHref(hop.id)} className="text-xs underline underline-offset-4">
                    evidence
                  </Link>
                </div>
                <HopEvidence id={hop.id} />
              </li>
            ))}
          </ol>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="outline" onClick={onReplay} disabled={revealed < hops.length}>
              Replay
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={onClear}>
              Clear
            </Button>
          </div>
        </>
      )}
      {!hops && (
        <p className="text-xs text-muted-foreground">
          The fewest hops from one region to another along these connections, drawn hop by hop with each hop&apos;s
          citations. Among routes as short, the one whose weakest hop is strongest.
        </p>
      )}
    </div>
  );
}
