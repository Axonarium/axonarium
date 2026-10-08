// The read queries of lib/data.ts, answered from the deploy's snapshot of the database instead of Supabase
// (Tier 1, ADR 0017). Each matches its Supabase query: the same filters, order and pages.

import { type BrainClaim, type BrainEdge, brainEdges, type BrainGap, brainGaps } from "./brain";
import { type AtlasRegion, isNeuronType, isUberon, type RegionName, uberonNames } from "./regions";
import type { Atlas, ConnectivityClaim, Counts, Edge, EdgeSummary, Gap, Source } from "./types";

export interface RegionDetail extends AtlasRegion {
  atlas: string;
  parent: string | null;
  amygdala: boolean;
}

export interface RegionPage {
  region: RegionDetail;
  children: RegionName[];
  outputs: BrainEdge[];
  inputs: BrainEdge[];
  /** Names of the parent and every connected region. */
  names: Record<string, RegionName>;
}

/** The snapshot's tables (build/dumps.py, write_snapshot): every row the database holds. */
export interface Tables {
  atlases: (Atlas & Record<string, unknown>)[];
  regions: (RegionDetail & Record<string, unknown>)[];
  sources: Source[];
  connectivity_claims: ConnectivityClaim[];
  homology_claims: unknown[];
  edges: Edge[];
  /** Absent from snapshots made before gap mode (ADR 0027). */
  gaps?: Gap[];
  neuron_types?: { id: string; name: string }[];
}

/** Postgres orders these text IDs byte by byte; so does this. */
const byId = <T extends { id: string }>(a: T, b: T) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
const sorted = <T extends { id: string }>(rows: T[]) => [...rows].sort(byId);
const pick = <T, K extends keyof T>(row: T, keys: readonly K[]) => Object.fromEntries(keys.map((k) => [k, row[k]])) as Pick<T, K>;

const SUMMARY = ["id", "subject_id", "predicate", "object_id", "species", "n_claims", "n_present", "n_absent", "strength", "density"] as const;
const NAME = ["id", "acronym", "name", "amygdala"] as const;
const DETAIL = ["id", "name", "acronym", "atlas", "parent", "uberon", "uberon_label", "amygdala"] as const;
const AMYGDALA = ["id", "acronym", "name", "uberon", "uberon_label"] as const;
const ATLAS = ["id", "name", "species", "version", "url", "brainglobe_name", "citation"] as const;

export function counts(t: Tables): Counts {
  return {
    claims: t.connectivity_claims.length + t.homology_claims.length,
    edges: t.edges.length,
    sources: t.sources.length,
    species: new Set(t.edges.map((e) => e.species)).size,
  };
}

export const edges = (t: Tables): EdgeSummary[] => sorted(t.edges).map((e) => pick(e, SUMMARY));

/** The species and predicates among some connections, each sorted: the explore page's filter choices. */
export function facetsOf(rows: { species: string; predicate: string }[]): { species: string[]; predicate: string[] } {
  const distinct = (key: "species" | "predicate") => [...new Set(rows.map((r) => r[key]))].sort();
  return { species: distinct("species"), predicate: distinct("predicate") };
}
export const edgeFacets = (t: Tables) => facetsOf(t.edges);
export const edge = (t: Tables, id: string): Edge | null => t.edges.find((e) => e.id === id) ?? null;
export const claims = (t: Tables, ids: string[]): ConnectivityClaim[] => sorted(t.connectivity_claims.filter((c) => ids.includes(c.id)));
export const claim = (t: Tables, id: string): ConnectivityClaim | null => t.connectivity_claims.find((c) => c.id === id) ?? null;
export const source = (t: Tables, id: string): Source | null => t.sources.find((s) => s.id === id) ?? null;

export function regionNames(t: Tables, ids: string[]): Record<string, RegionName> {
  const wanted = new Set(ids);
  const terms = ids.filter(isUberon);
  const mapped = sorted(t.regions.filter((r) => r.uberon !== null && terms.includes(r.uberon)));
  const types = (t.neuron_types ?? []).filter((n) => isNeuronType(n.id) && wanted.has(n.id));
  return {
    ...uberonNames(terms, mapped),
    ...Object.fromEntries(types.map((n) => [n.id, { id: n.id, acronym: null, name: n.name, kind: "neuron_type" as const }])),
    ...Object.fromEntries(t.regions.filter((r) => wanted.has(r.id)).map((r) => [r.id, pick(r, NAME)])),
  };
}

export function atlases(t: Tables): { atlas: Atlas; regions: number; amygdala: AtlasRegion[] }[] {
  return sorted(t.atlases).map((atlas) => ({
    atlas: pick(atlas, ATLAS),
    regions: t.regions.filter((r) => r.atlas === atlas.id).length,
    amygdala: sorted(t.regions.filter((r) => r.atlas === atlas.id && r.amygdala === true)).map((r) => pick(r, AMYGDALA)),
  }));
}

const asBrainClaim = (c: ConnectivityClaim): BrainClaim => pick(c, ["subject_id", "object_id", "status", "measurements", "terms"] as const);
const found = (c: ConnectivityClaim) => c.predicate === "projects_to" && c.result === "present" && c.status !== "retracted";

export function brain(t: Tables, atlas: string): BrainEdge[] {
  const drawn = sorted(t.edges.filter((e) => e.predicate === "projects_to" && e.subject_type === "region" && e.object_type === "region" && e.n_present > 0));
  const evidence = sorted(t.connectivity_claims.filter((c) => found(c) && c.subject_atlas === atlas && c.object_atlas === atlas));
  return brainEdges(drawn, evidence.map(asBrainClaim)).filter((e) => e.claims > 0);
}

export function gaps(t: Tables, atlas: string): BrainGap[] {
  return brainGaps(sorted((t.gaps ?? []).filter((g) => g.atlas === atlas)));
}

export function region(t: Tables, id: string): RegionPage | null {
  const row = t.regions.find((r) => r.id === id);
  if (!row) return null;
  const connected = (end: "subject_id" | "object_id") =>
    brainEdges(
      sorted(t.edges.filter((e) => e[end] === id && e.n_present > 0)),
      // Unlike brain(), any predicate: the same as the Supabase query this mirrors.
      sorted(t.connectivity_claims.filter((c) => c[end] === id && c.result === "present" && c.status !== "retracted")).map(asBrainClaim),
    ).sort((a, b) => (b.density ?? 0) - (a.density ?? 0));
  const outputs = connected("subject_id");
  const inputs = connected("object_id");
  const ids = [row.parent, ...outputs.map((e) => e.target), ...inputs.map((e) => e.source)].filter((x): x is string => !!x);
  return {
    region: pick(row, DETAIL),
    children: sorted(t.regions.filter((r) => r.parent === id)).map((r) => pick(r, ["id", "acronym", "name"] as const)),
    outputs,
    inputs,
    names: regionNames(t, [...new Set(ids)]),
  };
}

const page = <T>(rows: T[], limit: number, offset: number) => ({ items: rows.slice(offset, offset + limit), total: rows.length });

/** Letters, digits, spaces, hyphens, apostrophes and dots only: safe inside a PostgREST `or` filter. */
export const searchable = (q: string) => q.replace(/[^\p{L}\p{N} .'-]/gu, "").trim().slice(0, 100);

/** A page of regions; `q` matches part of an acronym or name, ignoring case, like the API's `ilike`. */
export function regionsPage(t: Tables, f: { q?: string | null; atlas?: string | null; amygdala?: boolean | null; limit: number; offset: number }) {
  const q = f.q ? searchable(f.q).toLowerCase() : "";
  const rows = sorted(t.regions).filter(
    (r) =>
      (!q || (r.acronym ?? "").toLowerCase().includes(q) || r.name.toLowerCase().includes(q)) &&
      (!f.atlas || r.atlas === f.atlas) &&
      (f.amygdala === null || f.amygdala === undefined || r.amygdala === f.amygdala),
  );
  return page(rows.map((r) => pick(r, DETAIL)), f.limit, f.offset);
}

/** A page of connections, strongest projection density first, then by ID; connections without a density last. */
export function connectionsPage(t: Tables, f: {
  subject?: string | null;
  object?: string | null;
  species?: string | null;
  predicate?: string | null;
  minDensity?: number | null;
  limit: number;
  offset: number;
}) {
  const min = f.minDensity;
  const rows = t.edges
    .filter(
      (e) =>
        (!f.subject || e.subject_id === f.subject) &&
        (!f.object || e.object_id === f.object) &&
        (!f.species || e.species === f.species) &&
        (!f.predicate || e.predicate === f.predicate) &&
        (min === null || min === undefined || (e.density !== null && e.density >= min)),
    )
    .sort((a, b) => (a.density === b.density ? byId(a, b) : a.density === null ? 1 : b.density === null ? -1 : b.density - a.density));
  return page(rows, f.limit, f.offset);
}
