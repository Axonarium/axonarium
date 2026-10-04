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
  /** In the amygdala, or one of its subdivisions (from UBERON; ADR 0009). */
  amygdala?: boolean;
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

/** The connections at or above a minimum density, strongest first. The minimum applies only to connections that
 * state a density: the others (literature claims rarely give one) are always kept, and listed last. */
export function byDensity(edges: BrainEdge[], minimum: number): BrainEdge[] {
  return edges
    .filter((e) => e.density === null || e.density >= minimum)
    .sort((a, b) => (a.density === null ? (b.density === null ? 0 : 1) : b.density === null ? -1 : b.density - a.density));
}

/** Arc width in pixels, by density relative to the strongest shown. */
export function arcWidth(density: number | null, strongest: number): number {
  return 0.75 + 4 * Math.sqrt(Math.max(0, density ?? 0) / (strongest || 1));
}

export interface NetworkNode {
  id: string;
  acronym: string;
  name: string;
  /** An amygdala region with injections. */
  injected: boolean;
  /** Connections shown into this region. */
  inputs: number;
}

export interface NetworkLink {
  id: string;
  source: string;
  target: string;
  /** The amygdala end, kept as an ID: the graph library replaces `source` and `target` with node objects. */
  from: string;
  density: number | null;
  accepted: number;
}

export type Direction = "outputs" | "inputs";

/** The amygdala end of a connection: its source among the outputs, its target among the inputs. */
export function hubOf(edge: BrainEdge, direction: Direction): string {
  return direction === "outputs" ? edge.source : edge.target;
}

/** The amygdala's outputs (from one of its regions) or its inputs (into one, from outside it), among the drawn
 * regions. Connections within the amygdala are outputs. */
export function directed(edges: BrainEdge[], regions: Record<string, BrainRegion>, direction: Direction): BrainEdge[] {
  return edges.filter((e) => {
    const source = regions[e.source];
    const target = regions[e.target];
    if (!source || !target) return false;
    return direction === "outputs" ? !!source.amygdala : !!target.amygdala && !source.amygdala;
  });
}

/** The network view's graph: a node per region, sorted by ID, and a fresh link per connection. */
export function networkData(
  shown: BrainEdge[],
  regions: Record<string, BrainRegion>,
  injected: string[],
  hub: (edge: BrainEdge) => string = (edge) => edge.source,
) {
  const inputs = new Map<string, number>();
  for (const edge of shown) {
    inputs.set(edge.source, inputs.get(edge.source) ?? 0);
    inputs.set(edge.target, (inputs.get(edge.target) ?? 0) + 1);
  }
  const nodes: NetworkNode[] = [...inputs.entries()]
    .sort(([a], [b]) => a.localeCompare(b, "en", { numeric: true }))
    .map(([id, n]) => ({ id, acronym: regions[id].acronym, name: regions[id].name, injected: injected.includes(id), inputs: n }));
  const links: NetworkLink[] = shown.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    from: hub(e),
    density: e.density,
    accepted: e.accepted,
  }));
  return { nodes, links };
}

/** How /brain?region=<id> opens: on an amygdala region's outputs, or its inputs if it has no injections; any
 * other region selected in the direction it appears in; null if no drawn connection names it. */
export function linkedView(
  edges: BrainEdge[],
  regions: Record<string, BrainRegion>,
  id: string,
): { direction: Direction; source?: string; selected?: string } | null {
  const outputs = directed(edges, regions, "outputs");
  const inputs = directed(edges, regions, "inputs");
  if (outputs.some((e) => e.source === id)) return { direction: "outputs", source: id };
  if (inputs.some((e) => e.target === id)) return { direction: "inputs", source: id };
  if (outputs.some((e) => e.target === id)) return { direction: "outputs", selected: id };
  if (inputs.some((e) => e.source === id)) return { direction: "inputs", selected: id };
  return null;
}
