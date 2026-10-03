// Read-only queries against the Supabase serving tables, with the public (publishable) key.
// Every query returns a Result, so a page can say "data unavailable" instead of failing.

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import type { ConnectivityClaim, Counts, Edge, Source } from "./types";

export type Result<T> = { ok: true; data: T } | { ok: false; reason: string };

function client(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  return url && key ? createClient(url, key, { auth: { persistSession: false } }) : null;
}

async function query<T>(run: (db: SupabaseClient) => PromiseLike<{ data: T | null; error: { message: string } | null }>): Promise<Result<T>> {
  const db = client();
  if (!db) return { ok: false, reason: "the database isn't configured for this build" };
  try {
    const { data, error } = await run(db);
    if (error) return { ok: false, reason: error.message };
    return { ok: true, data: data as T };
  } catch (error) {
    return { ok: false, reason: error instanceof Error ? error.message : "the database couldn't be reached" };
  }
}

async function count(table: string): Promise<Result<number>> {
  const db = client();
  if (!db) return { ok: false, reason: "the database isn't configured for this build" };
  try {
    const { count: n, error } = await db.from(table).select("*", { count: "exact", head: true });
    return error ? { ok: false, reason: error.message } : { ok: true, data: n ?? 0 };
  } catch (error) {
    return { ok: false, reason: error instanceof Error ? error.message : "the database couldn't be reached" };
  }
}

export async function getCounts(): Promise<Result<Counts>> {
  const [connectivity, homology, edges, sources, species] = await Promise.all([
    count("connectivity_claims"),
    count("homology_claims"),
    count("edges"),
    count("sources"),
    query<{ species: string }[]>((db) => db.from("edges").select("species")),
  ]);
  for (const part of [connectivity, homology, edges, sources, species]) if (!part.ok) return part;
  const value = <T,>(r: Result<T>) => (r as { ok: true; data: T }).data;
  return {
    ok: true,
    data: {
      claims: value(connectivity) + value(homology),
      edges: value(edges),
      sources: value(sources),
      species: new Set(value(species).map((row) => row.species)).size,
    },
  };
}

export function listEdges(): Promise<Result<Edge[]>> {
  return query<Edge[]>((db) => db.from("edges").select("*").order("id"));
}

export async function getEdge(id: string): Promise<Result<Edge | null>> {
  return query<Edge | null>((db) => db.from("edges").select("*").eq("id", id).maybeSingle());
}

export function getClaims(ids: string[]): Promise<Result<ConnectivityClaim[]>> {
  return query<ConnectivityClaim[]>((db) => db.from("connectivity_claims").select("*").in("id", ids).order("id"));
}

export function getClaim(id: string): Promise<Result<ConnectivityClaim | null>> {
  return query<ConnectivityClaim | null>((db) => db.from("connectivity_claims").select("*").eq("id", id).maybeSingle());
}

export function getSource(id: string): Promise<Result<Source | null>> {
  return query<Source | null>((db) => db.from("sources").select("*").eq("id", id).maybeSingle());
}
