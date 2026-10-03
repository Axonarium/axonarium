// Read-only queries against the Supabase serving tables, with the public (publishable) key. Server only.
//
// A build without the Supabase variables (pull-request CI) gets null, and pages say the data isn't connected.
// A configured database that fails throws, so Next.js keeps serving the last good page and shows app/error.tsx
// only when it has none.

import "server-only";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { fetchAll } from "./pages";
import type { RegionName } from "./regions";
import type { Atlas, ConnectivityClaim, Counts, Edge, EdgeSummary, Source } from "./types";

const EDGE_SUMMARY = "id, subject_id, predicate, object_id, species, n_claims, n_present, n_absent, strength";

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

/** Every atlas region, by ID (about a thousand rows, cached with the page). */
export async function getRegions(): Promise<Record<string, RegionName> | null> {
  const db = client();
  if (!db) return null;
  const all = await fetchAll((from, to) =>
    rows<RegionName[]>("regions", () => db.from("regions").select("id, acronym, name, atlas, uberon").order("id").range(from, to)),
  );
  return Object.fromEntries(all.map((region) => [region.id, region]));
}

export async function getAtlases(): Promise<Atlas[] | null> {
  const db = client();
  if (!db) return null;
  return rows<Atlas[]>("atlases", () => db.from("atlases").select("id, name, species, version, url, brainglobe_name, citation").order("id"));
}
