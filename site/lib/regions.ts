// Atlas regions on the site: labels for IDs, and the amygdala regions each atlas resolves.

/** The amygdala and the nuclei claims name, in display order. Mirrors AMYGDALA in ingest/atlases.py. */
export const AMYGDALA = [
  { uberon: "UBERON:0001876", label: "amygdala" },
  { uberon: "UBERON:0006107", label: "basolateral amygdaloid nuclear complex" },
  { uberon: "UBERON:0002886", label: "lateral amygdaloid nucleus" },
  { uberon: "UBERON:0002887", label: "basal amygdaloid nucleus" },
  { uberon: "UBERON:0002885", label: "accessory basal amygdaloid nucleus" },
  { uberon: "UBERON:0002883", label: "central amygdaloid nucleus" },
  { uberon: "UBERON:0002892", label: "medial amygdaloid nucleus" },
  { uberon: "UBERON:0006108", label: "corticomedial nuclear complex" },
  { uberon: "UBERON:0002890", label: "anterior amygdaloid area" },
  { uberon: "UBERON:0002884", label: "intercalated amygdaloid nuclei" },
] as const;

export interface RegionName {
  id: string;
  acronym: string | null;
  name: string;
  atlas: string;
  uberon: string | null;
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

/** The regions mapped to the amygdala or its nuclei, in the order of AMYGDALA. */
export function amygdalaRegions(regions: RegionName[]): RegionName[] {
  const order = (r: RegionName) => AMYGDALA.findIndex((term) => term.uberon === r.uberon);
  return regions.filter((r) => order(r) >= 0).sort((a, b) => order(a) - order(b) || a.id.localeCompare(b.id));
}
