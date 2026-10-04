// The regions index: every atlas region with a connection, with how many go out and come in.

import type { RegionName } from "./regions";

export interface IndexedRegion {
  id: string;
  acronym: string | null;
  name: string;
  amygdala: boolean;
  outputs: number;
  inputs: number;
}

/** Atlas regions named by these connections (others, such as UBERON terms, are left out): the amygdala's
 * first, then by acronym. */
export function regionIndex(
  edges: { subject_id: string; object_id: string }[],
  names: Record<string, RegionName & { amygdala?: boolean | null }>,
): IndexedRegion[] {
  const found = new Map<string, IndexedRegion>();
  const entry = (id: string) => {
    const name = names[id];
    if (!name) return null;
    if (!found.has(id))
      found.set(id, { id, acronym: name.acronym, name: name.name, amygdala: !!name.amygdala, outputs: 0, inputs: 0 });
    return found.get(id)!;
  };
  for (const edge of edges) {
    const from = entry(edge.subject_id);
    const to = entry(edge.object_id);
    if (from) from.outputs += 1;
    if (to) to.inputs += 1;
  }
  return [...found.values()].sort(
    (a, b) => Number(b.amygdala) - Number(a.amygdala) || (a.acronym ?? a.name).localeCompare(b.acronym ?? b.name),
  );
}
