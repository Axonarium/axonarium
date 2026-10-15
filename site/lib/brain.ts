// The 3D brain view's data: connections with their strongest projection density, and arc geometry.
// Meshes and centroids come from the build's mesh export (build/meshes.py, ADR 0011), in millimetres with
// x towards the animal's right, y up and z posterior. The view shows one module at a time, the circuit whose
// outputs and inputs it draws (ADR 0034).

import type { RegionName } from "./regions";
import type { Edge, Gap, Measurement } from "./types";

export type Point = [number, number, number];

export interface BrainEdge {
  id: string;
  source: string;
  target: string;
  /** The strongest projection density among the connection's claims, or null if none states one. */
  density: number | null;
  claims: number;
  accepted: number;
  /** Claims drafted from published papers rather than read from the Allen atlas (their terms say which; build/terms.py). */
  papers: number;
}

/** Gap mode (ADR 0027): an untested connection from a module's region nobody has injected, and the regions whose
 * connections to the same target suggest it. */
export interface BrainGap {
  id: string;
  source: string;
  target: string;
  density: number | null;
  /** The regions (a neighbour, or a subdivision of one) whose connections to the target suggest this one. */
  by: string[];
}

/** A gap as the viewer draws it: a connection with no claims. */
export const gapEdge = (gap: BrainGap): BrainEdge => ({
  id: gap.id,
  source: gap.source,
  target: gap.target,
  density: gap.density,
  claims: 0,
  accepted: 0,
  papers: 0,
});

/** The brain page's gaps, with each suggesting connection reduced to its region (its ID's first part). */
export function brainGaps(gaps: Pick<Gap, "id" | "subject_id" | "object_id" | "density" | "suggested_by">[]): BrainGap[] {
  return gaps.map((g) => ({
    id: g.id,
    source: g.subject_id,
    target: g.object_id,
    density: g.density,
    by: [...new Set(g.suggested_by.map((edge) => edge.split("|")[0]))],
  }));
}

export interface BrainRegion {
  acronym: string;
  name: string;
  file: string;
  centroid: Point;
  /** In the amygdala, or one of its subdivisions (from UBERON; ADR 0009). */
  amygdala?: boolean;
  /** The modules the region belongs to (ADR 0034); absent from meshes exported before modules. */
  modules?: string[];
}

/** The species the brain view switches between (ADR 0034). Human waits for human connectivity (Phase 7c). */
export type Species = "mouse" | "rat";

/** A module of data/modules.yaml: a circuit the brain view can centre on. */
export interface BrainModule {
  id: string;
  name: string;
}

/** The module the brain view opens on when none is chosen, the one Axonarium started with. */
export const FIRST_MODULE: BrainModule = { id: "amygdala", name: "Amygdala" };

/** Whether a region belongs to a module. Meshes exported before modules know only the amygdala. */
export function inModule(region: BrainRegion | undefined, module: string): boolean {
  if (!region) return false;
  return region.modules ? region.modules.includes(module) : module === FIRST_MODULE.id && !!region.amygdala;
}

/** "the amygdala", "the hippocampal formation": a module's name inside a sentence. */
export const moduleText = (module: BrainModule) => `the ${module.name.charAt(0).toLowerCase()}${module.name.slice(1)}`;

/**
 * The regions of a species with no meshes yet (the rat; ADR 0034), for the network view: named as the site names them
 * (UBERON terms by the atlas regions mapped to them; lib/regions.ts), the ID where nothing names them, and placed in
 * the modules whose UBERON terms include them.
 */
export function namedRegions(ids: string[], names: Record<string, RegionName>, modules: { id: string; terms: string[] }[]) {
  return Object.fromEntries(
    ids.map((id): [string, BrainRegion] => {
      const name = names[id];
      return [
        id,
        {
          acronym: name?.acronym ?? name?.name ?? id,
          name: name?.name ?? id,
          file: "",
          centroid: [0, 0, 0],
          modules: modules.filter((m) => m.terms.includes(id)).map((m) => m.id),
        },
      ];
    }),
  );
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
  /** "allen-institute" for claims from the Allen atlas; absent from snapshots made before it was read here. */
  terms?: string;
}

const key = (subject: string, object: string) => `${subject} ${object}`;

export function brainEdges(edges: Pick<Edge, "id" | "subject_id" | "object_id">[], claims: BrainClaim[]): BrainEdge[] {
  const found = new Map<string, BrainEdge>(
    edges.map((e) => [
      key(e.subject_id, e.object_id),
      { id: e.id, source: e.subject_id, target: e.object_id, density: null, claims: 0, accepted: 0, papers: 0 },
    ]),
  );
  for (const claim of claims) {
    const edge = found.get(key(claim.subject_id, claim.object_id));
    if (!edge) continue;
    edge.claims += 1;
    if (claim.status === "accepted") edge.accepted += 1;
    if (claim.terms !== undefined && claim.terms !== "allen-institute") edge.papers += 1;
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
  /** A module's region at the module's end of a connection shown (with injections, among the outputs). */
  injected: boolean;
  /** Connections shown into this region. */
  inputs: number;
}

export interface NetworkLink {
  id: string;
  source: string;
  target: string;
  /** The module's end, kept as an ID: the graph library replaces `source` and `target` with node objects. */
  from: string;
  density: number | null;
  accepted: number;
}

export type Direction = "outputs" | "inputs";

/** The module's end of a connection: its source among the outputs, its target among the inputs. */
export function hubOf(edge: BrainEdge, direction: Direction): string {
  return direction === "outputs" ? edge.source : edge.target;
}

/** A module's outputs (from one of its regions) or its inputs (into one, from outside it), among the drawn
 * regions. Connections within the module are outputs. */
export function directed(
  edges: BrainEdge[],
  regions: Record<string, BrainRegion>,
  direction: Direction,
  module: string = FIRST_MODULE.id,
): BrainEdge[] {
  return edges.filter((e) => {
    const source = regions[e.source];
    const target = regions[e.target];
    if (!source || !target) return false;
    return direction === "outputs" ? inModule(source, module) : inModule(target, module) && !inModule(source, module);
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

/** How /brain?region=<id> opens in a module: on a module region's outputs, or its inputs if it has no injections;
 * any other region selected in the direction it appears in; null if no drawn connection names it. */
export function linkedView(
  edges: BrainEdge[],
  regions: Record<string, BrainRegion>,
  id: string,
  module: string = FIRST_MODULE.id,
): { direction: Direction; source?: string; selected?: string } | null {
  const outputs = directed(edges, regions, "outputs", module);
  const inputs = directed(edges, regions, "inputs", module);
  if (outputs.some((e) => e.source === id)) return { direction: "outputs", source: id };
  if (inputs.some((e) => e.target === id)) return { direction: "inputs", source: id };
  if (outputs.some((e) => e.target === id)) return { direction: "outputs", selected: id };
  if (inputs.some((e) => e.source === id)) return { direction: "inputs", selected: id };
  return null;
}

/** The module /brain?region=<id> opens on, when the link names none: the first of the region's own modules, then of
 * the rest, where some drawn connection names the region. */
export function linkedModule(
  edges: BrainEdge[],
  regions: Record<string, BrainRegion>,
  id: string,
  modules: BrainModule[],
): string | null {
  const own = modules.filter((m) => inModule(regions[id], m.id));
  const order = [...own, ...modules.filter((m) => !own.includes(m))];
  return order.find((m) => linkedView(edges, regions, id, m.id) !== null)?.id ?? null;
}
