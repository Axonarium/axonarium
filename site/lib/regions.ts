// Atlas regions on the site: labels for IDs. Which regions belong to the amygdala is decided by the build
// (from UBERON's hierarchy; ADR 0009) and stored in the regions table.

import { regionHref } from "./format";

export interface RegionName {
  id: string;
  acronym: string | null;
  name: string;
  amygdala?: boolean | null;
  /** What the ID names: an atlas region (the default, with a page of its own), a UBERON term, or a neuron type. */
  kind?: "region" | "uberon" | "neuron_type";
}

export interface AtlasRegion extends RegionName {
  uberon: string | null;
  uberon_label: string | null;
}

export interface Label {
  short: string;
  long: string | null;
  id: string;
  /** The entity's page on the site, if it has one: atlas regions do. */
  href: string | null;
}

/** How to show an entity ID: by acronym and name when it has a name, linking atlas regions to their page; otherwise by
 * its ID alone. */
export function regionLabel(id: string, regions: Record<string, RegionName>): Label {
  const region = regions[id];
  if (!region) return { short: id, long: null, id, href: null };
  const page = !region.kind || region.kind === "region";
  return { short: region.acronym ?? region.name, long: region.name, id, href: page ? regionHref(id) : null };
}

/** An atlas region mapped to a UBERON term, as the regions table holds it. */
export interface MappedRegion {
  id: string;
  acronym: string | null;
  name: string;
  atlas: string;
  parent: string | null;
  uberon: string | null;
  uberon_label: string | null;
}

const PREFERRED_ATLAS = "allen-mouse-ccf-2017"; // its acronyms are the ones the extraction lexicon and papers use

/**
 * Names for UBERON terms, which rat and human claims use where mouse claims name Allen regions (ADR 0028), from the
 * atlas regions mapped to each term: the term's own label where the build has it (the amygdala's terms), else the name
 * of the highest region mapped to it, preferring the Allen mouse atlas. The acronym is that region's, but only when a
 * single region (with its subregions) maps to the term; several would make any one acronym a guess.
 */
export function uberonNames(terms: string[], mapped: MappedRegion[]): Record<string, RegionName> {
  const names: Record<string, RegionName> = {};
  const byId = (a: MappedRegion, b: MappedRegion) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  for (const term of new Set(terms)) {
    const group = mapped.filter((r) => r.uberon === term);
    if (group.length === 0) continue;
    const preferred = group.filter((r) => r.atlas === PREFERRED_ATLAS);
    const pool = preferred.length ? preferred : group;
    const inPool = new Set(pool.map((r) => r.id));
    const tops = pool.filter((r) => !inPool.has(r.parent ?? "")).sort(byId);
    const label = group.map((r) => r.uberon_label).find((l): l is string => !!l);
    names[term] = { id: term, acronym: tops.length === 1 ? tops[0].acronym : null, name: label ?? tops[0].name, kind: "uberon" };
  }
  return names;
}

/** Which IDs name UBERON terms and which name the project's neuron types. */
export const isUberon = (id: string) => id.startsWith("UBERON:");
export const isNeuronType = (id: string) => id.startsWith("nt-");
