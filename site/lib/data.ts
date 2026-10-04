// Read-only queries against the Supabase serving tables, with the public (publishable) key. Server only.
//
// When the database can't answer (paused, down, or not configured), each query is answered from the snapshot of
// the database that the deploy bundles with the site (Tier 1, ADR 0017). The snapshot holds exactly what the
// deploy loaded into the database, so the answers are the same.
//
// A build with neither (pull-request CI) gets null, and pages say the data isn't connected. A configured database
// that fails without a snapshot throws, so Next.js keeps serving the last good page and shows app/error.tsx only
// when it has none.

import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { type BrainClaim, type BrainEdge, brainEdges } from "./brain";
import * as offline from "./offline";
import type { RegionDetail, RegionPage, Tables } from "./offline";
import { fetchAll } from "./pages";
import { type IndexedRegion, regionIndex } from "./region-index";
import type { AtlasRegion, RegionName } from "./regions";
import type { Atlas, ConnectivityClaim, Counts, Edge, EdgeSummary, Source } from "./types";

export type { RegionDetail, RegionPage } from "./offline";

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

// The deploy writes it with `python -m build --snapshot site/snapshot/snapshot.json`; next.config.ts bundles it.
const SNAPSHOT = path.join(process.cwd(), "snapshot", "snapshot.json");
let snapshot: Promise<Tables | null> | undefined;

function loadSnapshot(): Promise<Tables | null> {
  snapshot ??= readFile(SNAPSHOT, "utf8").then(
    (text) => (JSON.parse(text) as { tables: Tables }).tables,
    () => null, // No snapshot: a pull request's build, or local development.
  );
  return snapshot;
}

/** The database's answer; the snapshot's when the database fails or isn't configured; `none` with neither. */
async function read<T, N = null>(live: (db: SupabaseClient) => Promise<T>, fallback: (tables: Tables) => T, none: N): Promise<T | N> {
  const db = client();
  if (db) {
    try {
      return await live(db);
    } catch (error) {
      const tables = await loadSnapshot();
      if (!tables) throw error;
      console.error("Answering from the snapshot instead.");
      return fallback(tables);
    }
  }
  const tables = await loadSnapshot();
  return tables ? fallback(tables) : none;
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

export function getCounts(): Promise<Counts | null> {
  return read(async (db) => {
    const [connectivity, homology, edges, sources, species] = await Promise.all([
      count(db, "connectivity_claims"),
      count(db, "homology_claims"),
      count(db, "edges"),
      count(db, "sources"),
      fetchAll((from, to) => rows<{ species: string }[]>("edge species", () => db.from("edges").select("species").order("id").range(from, to))),
    ]);
    return { claims: connectivity + homology, edges, sources, species: new Set(species.map((row) => row.species)).size };
  }, offline.counts, null);
}

export function listEdges(): Promise<EdgeSummary[] | null> {
  return read(
    (db) => fetchAll((from, to) => rows<EdgeSummary[]>("edges", () => db.from("edges").select(EDGE_SUMMARY).order("id").range(from, to))),
    offline.edges,
    null,
  );
}

export function getEdge(id: string): Promise<Edge | null | undefined> {
  return read((db) => rows<Edge | null>("edge", () => db.from("edges").select("*").eq("id", id).maybeSingle()), (t) => offline.edge(t, id), undefined);
}

export function getClaims(ids: string[]): Promise<ConnectivityClaim[]> {
  return read(
    (db) => rows<ConnectivityClaim[]>("claims", () => db.from("connectivity_claims").select("*").in("id", ids).order("id")),
    (t) => offline.claims(t, ids),
    [],
  );
}

export function getClaim(id: string): Promise<ConnectivityClaim | null | undefined> {
  return read(
    (db) => rows<ConnectivityClaim | null>("claim", () => db.from("connectivity_claims").select("*").eq("id", id).maybeSingle()),
    (t) => offline.claim(t, id),
    undefined,
  );
}

export function getSource(id: string): Promise<Source | null> {
  return read((db) => rows<Source | null>("source", () => db.from("sources").select("*").eq("id", id).maybeSingle()), (t) => offline.source(t, id), null);
}

/** The names of these atlas regions, by ID (IDs that aren't atlas regions are left out). */
export async function getRegionNames(ids: string[]): Promise<Record<string, RegionName>> {
  if (ids.length === 0) return {};
  return read(
    async (db) => {
      const chunks = Array.from({ length: Math.ceil(ids.length / 200) }, (_, i) => ids.slice(i * 200, i * 200 + 200));
      const found = await Promise.all(
        chunks.map((chunk) => rows<RegionName[]>("region names", () => db.from("regions").select("id, acronym, name, amygdala").in("id", chunk))),
      );
      return Object.fromEntries(found.flat().map((region) => [region.id, region]));
    },
    (t) => offline.regionNames(t, ids),
    {},
  );
}

/** Each atlas, with its number of regions and the regions UBERON places under the amygdala. */
export function getAtlases(): Promise<{ atlas: Atlas; regions: number; amygdala: AtlasRegion[] }[] | null> {
  return read(async (db) => {
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
  }, offline.atlases, null);
}

async function countWhere(db: SupabaseClient, table: string, column: string, value: string): Promise<number> {
  const { count: n, error } = await db.from(table).select("*", { count: "exact", head: true }).eq(column, value);
  if (error) failed(`count ${table}`, error);
  return n ?? 0;
}

/** Region-to-region connections in one atlas, with their strongest projection density, for the 3D view. */
export function getBrainEdges(atlas: string): Promise<BrainEdge[] | null> {
  return read((db) => liveBrainEdges(db, atlas), (t) => offline.brain(t, atlas), null);
}

async function liveBrainEdges(db: SupabaseClient, atlas: string): Promise<BrainEdge[]> {
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

/** An atlas region with its subregions and its connections both ways, each with its strongest density. */
export function getRegion(id: string): Promise<RegionPage | null | undefined> {
  return read((db) => liveRegion(db, id), (t) => offline.region(t, id), undefined);
}

async function liveRegion(db: SupabaseClient, id: string): Promise<RegionPage | null> {
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

type RegionsFilter = { q?: string | null; atlas?: string | null; amygdala?: boolean | null; limit: number; offset: number };

/** A page of atlas regions (read API), by ID, optionally matching part of a name or acronym. */
export function listRegions(f: RegionsFilter): Promise<{ items: RegionDetail[]; total: number } | null> {
  return read((db) => liveRegions(db, f), (t) => offline.regionsPage(t, f), null);
}

async function liveRegions(db: SupabaseClient, f: RegionsFilter) {
  let query = db.from("regions").select("id, name, acronym, atlas, parent, uberon, uberon_label, amygdala", { count: "exact" });
  const q = f.q ? offline.searchable(f.q) : "";
  if (q) query = query.or(`acronym.ilike.*${q}*,name.ilike.*${q}*`);
  if (f.atlas) query = query.eq("atlas", f.atlas);
  if (f.amygdala !== null && f.amygdala !== undefined) query = query.eq("amygdala", f.amygdala);
  const { data, count: total, error } = await query.order("id").range(f.offset, f.offset + f.limit - 1);
  if (error) failed("regions page", error);
  return { items: (data ?? []) as RegionDetail[], total: total ?? 0 };
}

type ConnectionsFilter = {
  subject?: string | null;
  object?: string | null;
  species?: string | null;
  predicate?: string | null;
  minDensity?: number | null;
  limit: number;
  offset: number;
};

/** A page of connections (read API), strongest projection density first. */
export function listConnections(f: ConnectionsFilter): Promise<{ items: Edge[]; total: number } | null> {
  return read((db) => liveConnections(db, f), (t) => offline.connectionsPage(t, f), null);
}

async function liveConnections(db: SupabaseClient, f: ConnectionsFilter) {
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
