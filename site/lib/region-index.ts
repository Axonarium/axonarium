// The regions index: every atlas region with a connection, with how many go out and come in.

import type { RegionName } from "./regions";

export interface IndexedRegion {
  id: string;
  acronym: string | null;
  name: string;
  amygdala: boolean;
  /** The modules the region belongs to (ADR 0034). */
  modules: string[];
  outputs: number;
  inputs: number;
}

/** Atlas regions named by these connections (others, such as UBERON terms, are left out): those of the modules
 * first, by the modules' order (ADR 0034), then by acronym. Names from before modules place the amygdala's first. */
export function regionIndex(
  edges: { subject_id: string; object_id: string }[],
  names: Record<string, RegionName>,
  order: string[] = ["amygdala"],
): IndexedRegion[] {
  const found = new Map<string, IndexedRegion>();
  const entry = (id: string) => {
    const name = names[id];
    if (!name) return null;
    if (!found.has(id))
      found.set(id, {
        id,
        acronym: name.acronym,
        name: name.name,
        amygdala: !!name.amygdala,
        modules: name.modules ?? (name.amygdala ? ["amygdala"] : []),
        outputs: 0,
        inputs: 0,
      });
    return found.get(id)!;
  };
  for (const edge of edges) {
    const from = entry(edge.subject_id);
    const to = entry(edge.object_id);
    if (from) from.outputs += 1;
    if (to) to.inputs += 1;
  }
  // A region's place: its first module's, or after every module's for none.
  const rank = (r: IndexedRegion) => Math.min(...r.modules.map((m) => (order.includes(m) ? order.indexOf(m) : order.length)), order.length);
  return [...found.values()].sort((a, b) => rank(a) - rank(b) || (a.acronym ?? a.name).localeCompare(b.acronym ?? b.name));
}
