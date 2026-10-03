// Atlas regions on the site: labels for IDs. Which regions belong to the amygdala is decided by the build
// (from UBERON's hierarchy; ADR 0009) and stored in the regions table.

export interface RegionName {
  id: string;
  acronym: string | null;
  name: string;
}

export interface AtlasRegion extends RegionName {
  uberon: string | null;
  uberon_label: string | null;
}

export interface Label {
  short: string;
  long: string | null;
  id: string;
}

/** How to show an entity ID: an atlas region by acronym and name; anything else (UBERON, neuron types) by its ID. */
export function regionLabel(id: string, regions: Record<string, RegionName>): Label {
  const region = regions[id];
  return region ? { short: region.acronym ?? region.name, long: region.name, id } : { short: id, long: null, id };
}
