// The 3D brain view's data: connections with their strongest projection density, and arc geometry.
// Meshes and centroids come from the build's mesh export (build/meshes.py, ADR 0011), in millimetres with
// x towards the animal's right, y up and z posterior.

import type { Edge, Measurement } from "./types";

export type Point = [number, number, number];

export interface BrainEdge {
  id: string;
  source: string;
  target: string;
  /** The strongest projection density among the connection's claims, or null if none states one. */
  density: number | null;
  claims: number;
  accepted: number;
}

export interface BrainRegion {
  acronym: string;
  name: string;
  file: string;
  centroid: Point;
}

/** index.json of one atlas's meshes. */
export interface BrainIndex {
  atlas: string;
  root: string;
  regions: Record<string, BrainRegion>;
}

export interface BrainClaim {
  subject_id: string;
  object_id: string;
  status: string;
  measurements: Measurement[] | null;
}

const key = (subject: string, object: string) => `${subject} ${object}`;

export function brainEdges(edges: Pick<Edge, "id" | "subject_id" | "object_id">[], claims: BrainClaim[]): BrainEdge[] {
  const found = new Map<string, BrainEdge>(
    edges.map((e) => [
      key(e.subject_id, e.object_id),
      { id: e.id, source: e.subject_id, target: e.object_id, density: null, claims: 0, accepted: 0 },
    ]),
  );
  for (const claim of claims) {
    const edge = found.get(key(claim.subject_id, claim.object_id));
    if (!edge) continue;
    edge.claims += 1;
    if (claim.status === "accepted") edge.accepted += 1;
    for (const m of claim.measurements ?? []) {
      if (m.quantity === "projection_density" && (edge.density === null || m.value > edge.density)) edge.density = m.value;
    }
  }
  return [...found.values()];
}

/** The control point of an arc from a to b: the midpoint, lifted by a third of the distance. */
export function arcMidpoint(a: Point, b: Point): Point {
  const distance = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + distance / 3, (a[2] + b[2]) / 2];
}

/** Arc width in pixels, by density relative to the strongest shown. */
export function arcWidth(density: number | null, strongest: number): number {
  return 0.75 + 4 * Math.sqrt(Math.max(0, density ?? 0) / (strongest || 1));
}
