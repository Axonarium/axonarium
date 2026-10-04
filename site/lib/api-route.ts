// How every read-API route answers: JSON, cached at Vercel's edge for five minutes, with an error body and the
// right status when something is wrong (ADR 0013).

import "server-only";

import { BadRequest } from "./api";

const CACHE = "public, max-age=60, s-maxage=300, stale-while-revalidate=3600";

export class NotFound extends Error {}

export async function answer(produce: () => Promise<unknown>): Promise<Response> {
  try {
    const body = await produce();
    if (body === null || body === undefined) return Response.json({ error: "This deployment isn't connected to the database." }, { status: 503 });
    return Response.json(body, { headers: { "Cache-Control": CACHE, "Access-Control-Allow-Origin": "*" } });
  } catch (error) {
    if (error instanceof BadRequest) return Response.json({ error: error.message }, { status: 400 });
    if (error instanceof NotFound) return Response.json({ error: error.message }, { status: 404, headers: { "Cache-Control": CACHE } });
    console.error(error);
    return Response.json({ error: "The database couldn't be read." }, { status: 503 });
  }
}

/** A boolean query parameter: true, false, or absent (null); anything else is a bad request. */
export function flag(params: URLSearchParams, name: string): boolean | null {
  const raw = params.get(name);
  if (raw === null) return null;
  if (raw === "true" || raw === "false") return raw === "true";
  throw new BadRequest(`${name} must be true or false`);
}

/** A non-negative number query parameter, or null when absent. */
export function number(params: URLSearchParams, name: string): number | null {
  const raw = params.get(name);
  if (raw === null) return null;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) throw new BadRequest(`${name} must be a number of 0 or more`);
  return value;
}
