// The read API's response shapes and parameters (ADR 0013). Pure, so lib/api.test.ts can check every shape
// against the OpenAPI contract in lib/openapi.ts.

import type { BrainEdge } from "./brain";
import type { RegionDetail, RegionPage } from "./data";
import type { RegionName } from "./regions";
import type { ConnectivityClaim, Edge, Source } from "./types";

export interface Terms {
  id: string;
  name: string;
  url: string;
  note?: string;
}

/** What each terms tag (build/terms.py) means for someone reusing the data. */
export const TERMS: Record<string, Terms> = {
  "cc-by-4.0": {
    id: "cc-by-4.0",
    name: "CC BY 4.0",
    url: "https://creativecommons.org/licenses/by/4.0/",
    note: "Project-curated. Credit Axonarium and the cited source.",
  },
  "allen-institute": {
    id: "allen-institute",
    name: "Allen Institute terms of use",
    url: "https://alleninstitute.org/terms-of-use/",
    note:
      "Made from the Allen Mouse Brain Connectivity Atlas (Oh et al. 2014, doi:10.1038/nature13186). " +
      "Non-commercial use with attribution; not redistributed in Axonarium's dumps.",
  },
};

export class BadRequest extends Error {}

export const ref = (id: string, names: Record<string, RegionName>) => ({
  id,
  acronym: names[id]?.acronym ?? null,
  name: names[id]?.name ?? null,
});

export const toRegion = (r: RegionDetail) => ({
  id: r.id,
  acronym: r.acronym,
  name: r.name,
  atlas: r.atlas,
  parent: r.parent,
  uberon: r.uberon,
  uberon_label: r.uberon_label,
  amygdala: r.amygdala ?? null,
});

export const toConnection = (e: Edge, names: Record<string, RegionName>) => ({
  id: e.id,
  subject: ref(e.subject_id, names),
  predicate: e.predicate,
  object: ref(e.object_id, names),
  species: e.species,
  claims: e.n_claims,
  present: e.n_present,
  absent: e.n_absent,
  density: e.density,
  evidence_classes: e.evidence_classes,
  terms: e.terms,
});

export const toClaim = (c: ConnectivityClaim) => ({
  id: c.id,
  subject: { type: c.subject_type, id: c.subject_id, atlas: c.subject_atlas },
  predicate: c.predicate,
  object: { type: c.object_type, id: c.object_id, atlas: c.object_atlas },
  species: c.species,
  evidence_class: c.evidence_class,
  result: c.result,
  sign: c.sign,
  strength: c.strength,
  measurements: c.measurements,
  citation: { source: c.source_key, doi: c.doi, pmid: c.pmid, pmcid: c.pmcid, arxiv: c.arxiv, locator: c.locator },
  paraphrase: c.paraphrase,
  excerpt: c.excerpt,
  curation: c.curation,
  verification: c.verification,
  status: c.status,
  extra: c.extra,
  terms: TERMS[c.terms] ?? TERMS["cc-by-4.0"],
});

export const toSource = (s: Source) => ({
  id: s.id,
  title: s.title,
  year: s.year,
  journal: s.journal,
  kind: s.kind,
  license: s.license,
  open_access: s.open_access,
  retracted: s.retracted,
});

const link = (e: BrainEdge, other: string, names: Record<string, RegionName>) => ({
  connection: e.id,
  region: ref(other, names),
  density: e.density,
  claims: e.claims,
  accepted: e.accepted,
});

export const regionDetail = (page: RegionPage) => ({
  region: toRegion(page.region),
  subregions: page.children.map((c) => ({ id: c.id, acronym: c.acronym, name: c.name })),
  outputs: page.outputs.map((e) => link(e, e.target, page.names)),
  inputs: page.inputs.map((e) => link(e, e.source, page.names)),
});

/** `limit` (1–200, default 50) and `offset` (0 or more) from a query string; BadRequest otherwise. */
export function paging(params: URLSearchParams): { limit: number; offset: number } {
  const integer = (name: string, fallback: number, min: number, max: number) => {
    const raw = params.get(name);
    if (raw === null) return fallback;
    const value = Number(raw);
    if (!Number.isInteger(value) || value < min || value > max) throw new BadRequest(`${name} must be an integer from ${min} to ${max}`);
    return value;
  };
  return { limit: integer("limit", 50, 1, 200), offset: integer("offset", 0, 0, Number.MAX_SAFE_INTEGER) };
}
