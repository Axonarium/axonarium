// Read-only queries against the Supabase serving tables, with the public (publishable) key. Server only.
//
// A build without the Supabase variables (pull-request CI) gets null, and pages say the data isn't connected.
// A configured database that fails throws, so Next.js keeps serving the last good page and shows app/error.tsx
// only when it has none.

import "server-only";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { type BrainClaim, type BrainEdge, brainEdges } from "./brain";
import { fetchAll } from "./pages";
import { type IndexedRegion, regionIndex } from "./region-index";
import type { AtlasRegion, RegionName } from "./regions";
import type { Atlas, ConnectivityClaim, Counts, Edge, EdgeSummary, Source } from "./types";

const EDGE_SUMMARY = "id, subject_id, predicate, object_id, species, n_claims, n_present, n_absent, strength, density";

function client(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  return url && key ? createClient(url, key, { auth: { persistSession: false }, db: { timeout: 10_000 } }) : null;
}

function failed(what: string, error: { message: string }): never {
  console.error(`Supabase query failed (${what}): ${error.message}`);
  throw new Error("The database couldn't be read.");
}

async function rows<T>(what: string, run: () => PromiseLike<{ data: T | null; error: { message: string } | null }>): Promise<T> {
  const { data, error } = await run();
  if (error) failed(what, error);
  return data as T;
}

async function count(db: SupabaseClient, table: string): Promise<number> {
  const { count: n, error } = await db.from(table).select("*", { count: "exact", head: true });
  if (error) failed(`count ${table}`, error);
  return n ?? 0;
}

export async function getCounts(): Promise<Counts | null> {
  const db = client();
  if (!db) return null;
  const [connectivity, homology, edges, sources, species] = await Promise.all([
    count(db, "connectivity_claims"),
    count(db, "homology_claims"),
    count(db, "edges"),
    count(db, "sources"),
    fetchAll((from, to) => rows<{ species: string }[]>("edge species", () => db.from("edges").select("species").order("id").range(from, to))),
  ]);
  return { claims: connectivity + homology, edges, sources, species: new Set(species.map((row) => row.species)).size };
}

export async function listEdges(): Promise<EdgeSummary[] | null> {
  const db = client();
  if (!db) return null;
  return fetchAll((from, to) => rows<EdgeSummary[]>("edges", () => db.from("edges").select(EDGE_SUMMARY).order("id").range(from, to)));
}

export async function getEdge(id: string): Promise<Edge | null | undefined> {
  const db = client();
  if (!db) return undefined;
  return rows<Edge | null>("edge", () => db.from("edges").select("*").eq("id", id).maybeSingle());
}

export async function getClaims(ids: string[]): Promise<ConnectivityClaim[]> {
  const db = client();
  if (!db) return [];
  return rows<ConnectivityClaim[]>("claims", () => db.from("connectivity_claims").select("*").in("id", ids).order("id"));
}

export async function getClaim(id: string): Promise<ConnectivityClaim | null | undefined> {
  const db = client();
  if (!db) return undefined;
  return rows<ConnectivityClaim | null>("claim", () => db.from("connectivity_claims").select("*").eq("id", id).maybeSingle());
}

export async function getSource(id: string): Promise<Source | null> {
  const db = client();
  if (!db) return null;
  return rows<Source | null>("source", () => db.from("sources").select("*").eq("id", id).maybeSingle());
}

/** The names of these atlas regions, by ID (IDs that aren't atlas regions are left out). */
export async function getRegionNames(ids: string[]): Promise<Record<string, RegionName>> {
  const db = client();
  if (!db || ids.length === 0) return {};
  const chunks = Array.from({ length: Math.ceil(ids.length / 200) }, (_, i) => ids.slice(i * 200, i * 200 + 200));
  const found = await Promise.all(
    chunks.map((chunk) => rows<RegionName[]>("region names", () => db.from("regions").select("id, acronym, name, amygdala").in("id", chunk))),
  );
  return Object.fromEntries(found.flat().map((region) => [region.id, region]));
}

/** Each atlas, with its number of regions and the regions UBERON places under the amygdala. */
export async function getAtlases(): Promise<{ atlas: Atlas; regions: number; amygdala: AtlasRegion[] }[] | null> {
  const db = client();
  if (!db) return null;
  const atlases = await rows<Atlas[]>("atlases", () =>
    db.from("atlases").select("id, name, species, version, url, brainglobe_name, citation").order("id"),
  );
  return Promise.all(
    atlases.map(async (atlas) => ({
      atlas,
      regions: await countWhere(db, "regions", "atlas", atlas.id),
      amygdala: await rows<AtlasRegion[]>("amygdala regions", () =>
        db.from("regions").select("id, acronym, name, uberon, uberon_label").eq("atlas", atlas.id).eq("amygdala", true).order("id"),
      ),
    })),
  );
}

async function countWhere(db: SupabaseClient, table: string, column: string, value: string): Promise<number> {
  const { count: n, error } = await db.from(table).select("*", { count: "exact", head: true }).eq(column, value);
  if (error) failed(`count ${table}`, error);
  return n ?? 0;
}

/** Region-to-region connections in one atlas, with their strongest projection density, for the 3D view. */
export async function getBrainEdges(atlas: string): Promise<BrainEdge[] | null> {
  const db = client();
  if (!db) return null;
  const [edges, claims] = await Promise.all([
    fetchAll((from, to) =>
      rows<Pick<Edge, "id" | "subject_id" | "object_id">[]>("brain edges", () =>
        db.from("edges").select("id, subject_id, object_id").eq("predicate", "projects_to").eq("subject_type", "region")
          .eq("object_type", "region").gt("n_present", 0).order("id").range(from, to),
      ),
    ),
    fetchAll((from, to) =>
      rows<BrainClaim[]>("brain claims", () =>
        db.from("connectivity_claims").select("subject_id, object_id, status, measurements").eq("predicate", "projects_to")
          .eq("result", "present").neq("status", "retracted").eq("subject_atlas", atlas).eq("object_atlas", atlas).order("id").range(from, to),
      ),
    ),
  ]);
  return brainEdges(edges, claims).filter((edge) => edge.claims > 0);
}

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

/** An atlas region with its subregions and its connections both ways, each with its strongest density. */
export async function getRegion(id: string): Promise<RegionPage | null | undefined> {
  const db = client();
  if (!db) return undefined;
  const region = await rows<RegionDetail | null>("region", () =>
    db.from("regions").select("id, name, acronym, atlas, parent, uberon, uberon_label, amygdala").eq("id", id).maybeSingle(),
  );
  if (!region) return null;
  const connected = (end: "subject_id" | "object_id") =>
    Promise.all([
      fetchAll((from, to) =>
        rows<Pick<Edge, "id" | "subject_id" | "object_id">[]>("region edges", () =>
          db.from("edges").select("id, subject_id, object_id").eq(end, id).gt("n_present", 0).order("id").range(from, to),
        ),
      ),
      fetchAll((from, to) =>
        rows<BrainClaim[]>("region claims", () =>
          db.from("connectivity_claims").select("subject_id, object_id, status, measurements").eq(end, id)
            .eq("result", "present").neq("status", "retracted").order("id").range(from, to),
        ),
      ),
    ]).then(([edges, claims]) => brainEdges(edges, claims).sort((a, b) => (b.density ?? 0) - (a.density ?? 0)));
  const [children, outputs, inputs] = await Promise.all([
    rows<RegionName[]>("subregions", () => db.from("regions").select("id, acronym, name").eq("parent", id).order("id")),
    connected("subject_id"),
    connected("object_id"),
  ]);
  const ids = [region.parent, ...outputs.map((e) => e.target), ...inputs.map((e) => e.source)].filter((x): x is string => !!x);
  return { region, children, outputs, inputs, names: await getRegionNames([...new Set(ids)]) };
}

/** Every atlas region with a connection, with its numbers of outputs and inputs. */
export async function getRegionIndex(): Promise<IndexedRegion[] | null> {
  const edges = await listEdges();
  if (edges === null) return null;
  const names = await getRegionNames([...new Set(edges.flatMap((e) => [e.subject_id, e.object_id]))]);
  return regionIndex(edges, names);
}

/** Letters, digits, spaces, hyphens, apostrophes and dots only: safe inside a PostgREST `or` filter. */
const searchable = (q: string) => q.replace(/[^\p{L}\p{N} .'-]/gu, "").trim().slice(0, 100);

/** A page of atlas regions (read API), by ID, optionally matching part of a name or acronym. */
export async function listRegions(f: { q?: string | null; atlas?: string | null; amygdala?: boolean | null; limit: number; offset: number }) {
  const db = client();
  if (!db) return null;
  let query = db.from("regions").select("id, name, acronym, atlas, parent, uberon, uberon_label, amygdala", { count: "exact" });
  const q = f.q ? searchable(f.q) : "";
  if (q) query = query.or(`acronym.ilike.*${q}*,name.ilike.*${q}*`);
  if (f.atlas) query = query.eq("atlas", f.atlas);
  if (f.amygdala !== null && f.amygdala !== undefined) query = query.eq("amygdala", f.amygdala);
  const { data, count: total, error } = await query.order("id").range(f.offset, f.offset + f.limit - 1);
  if (error) failed("regions page", error);
  return { items: (data ?? []) as RegionDetail[], total: total ?? 0 };
}

/** A page of connections (read API), strongest projection density first. */
export async function listConnections(f: {
  subject?: string | null;
  object?: string | null;
  species?: string | null;
  predicate?: string | null;
  minDensity?: number | null;
  limit: number;
  offset: number;
}) {
  const db = client();
  if (!db) return null;
  let query = db.from("edges").select("*", { count: "exact" });
  if (f.subject) query = query.eq("subject_id", f.subject);
  if (f.object) query = query.eq("object_id", f.object);
  if (f.species) query = query.eq("species", f.species);
  if (f.predicate) query = query.eq("predicate", f.predicate);
  if (f.minDensity !== null && f.minDensity !== undefined) query = query.gte("density", f.minDensity);
  const { data, count: total, error } = await query
    .order("density", { ascending: false, nullsFirst: false })
    .order("id")
    .range(f.offset, f.offset + f.limit - 1);
  if (error) failed("connections page", error);
  return { items: (data ?? []) as Edge[], total: total ?? 0 };
}
