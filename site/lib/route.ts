// The path finder (sprint 3.5): routes from one region to another along cited connections, which the brain viewer
// animates hop by hop. Connections are directed, from the region that sends axons to the one that receives them.

import type { BrainEdge } from "./brain";

function outgoing(edges: BrainEdge[]): Map<string, BrainEdge[]> {
  const out = new Map<string, BrainEdge[]>();
  for (const edge of edges) {
    if (edge.source === edge.target) continue;
    const list = out.get(edge.source);
    if (list) list.push(edge);
    else out.set(edge.source, [edge]);
  }
  return out;
}

/** Every region a route from `from` can reach, `from` aside. */
export function reachable(edges: BrainEdge[], from: string): Set<string> {
  const out = outgoing(edges);
  const seen = new Set([from]);
  const queue = [from];
  while (queue.length) {
    for (const edge of out.get(queue.shift()!) ?? []) {
      if (seen.has(edge.target)) continue;
      seen.add(edge.target);
      queue.push(edge.target);
    }
  }
  seen.delete(from);
  return seen;
}

/** The route from `from` to `to` with the fewest hops; among those, the one whose weakest hop is strongest (a hop
 * that states no density counts as 0), then the first by connection ID. Null if no route exists. */
export function shortestRoute(edges: BrainEdge[], from: string, to: string): BrainEdge[] | null {
  if (from === to) return null;
  const out = outgoing(edges);
  // Breadth first, a layer at a time. Every shortest route to a region comes through the layer before it, so the
  // best weakest hop over those routes is known once that layer is done.
  const best = new Map<string, { weakest: number; via: BrainEdge | null }>([[from, { weakest: Infinity, via: null }]]);
  let layer = [from];
  while (layer.length && !best.has(to)) {
    const next = new Map<string, { weakest: number; via: BrainEdge }>();
    for (const id of layer) {
      const reach = best.get(id)!.weakest;
      for (const edge of out.get(id) ?? []) {
        if (best.has(edge.target)) continue;
        const weakest = Math.min(reach, edge.density ?? 0);
        const found = next.get(edge.target);
        if (!found || weakest > found.weakest || (weakest === found.weakest && edge.id < found.via.id)) {
          next.set(edge.target, { weakest, via: edge });
        }
      }
    }
    for (const [id, entry] of next) best.set(id, entry);
    layer = [...next.keys()];
  }
  if (!best.has(to)) return null;
  const hops: BrainEdge[] = [];
  for (let at = to; at !== from; ) {
    const via = best.get(at)!.via!;
    hops.unshift(via);
    at = via.source;
  }
  return hops;
}
