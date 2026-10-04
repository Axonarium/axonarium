import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

import { paging, regionDetail, TERMS, toClaim, toConnection, toRegion, toSource } from "./api";
import { openapi } from "./openapi";
import type { ConnectivityClaim, Edge, Source } from "./types";

const ajv = new Ajv2020({ strict: false, validateFormats: false });
ajv.addSchema(openapi as object, "api");
const conforms = (schema: string, value: unknown) => {
  const validate = ajv.getSchema(`api#/components/schemas/${schema}`)!;
  const ok = validate(value);
  if (!ok) throw new Error(JSON.stringify(validate.errors));
  return ok;
};

const edge: Edge = {
  id: "MBA:295|projects_to|MBA:672|NCBITaxon:10090",
  subject_id: "MBA:295",
  subject_type: "region",
  predicate: "projects_to",
  object_id: "MBA:672",
  object_type: "region",
  species: "NCBITaxon:10090",
  n_claims: 2,
  n_present: 2,
  n_absent: 0,
  n_ambiguous: 0,
  n_disputed: 0,
  evidence_classes: ["anterograde_tracer"],
  strength: null,
  signs: ["unknown"],
  claim_ids: ["clm-a", "clm-b"],
  density: 0.42,
  terms: ["allen-institute"],
};
const names = { "MBA:295": { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus" } };
const claim: ConnectivityClaim = {
  id: "clm-a",
  subject_type: "region",
  subject_id: "MBA:295",
  subject_atlas: "allen-mouse-ccf-2017",
  predicate: "projects_to",
  object_type: "region",
  object_id: "MBA:672",
  object_atlas: "allen-mouse-ccf-2017",
  species: "NCBITaxon:10090",
  evidence_class: "anterograde_tracer",
  result: "present",
  sign: "unknown",
  strength: null,
  measurements: [{ quantity: "projection_density", value: 0.42, unit: "1" }],
  source_key: "doi:10.1038/nature13186",
  doi: "10.1038/nature13186",
  pmid: null,
  pmcid: null,
  arxiv: null,
  locator: "Allen Mouse Brain Connectivity Atlas, experiment 1",
  paraphrase: "…",
  excerpt: null,
  curation: { by: "agent", role: "ingester", date: "2026-10-03" },
  verification: null,
  status: "accepted",
  extra: { "allen.experiment": 1 },
  terms: "allen-institute",
};

describe("the read API's shapes", () => {
  it("connections name their regions and list their terms", () => {
    const shaped = toConnection(edge, names);
    expect(shaped.subject).toEqual({ id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus" });
    expect(shaped.object).toEqual({ id: "MBA:672", acronym: null, name: null });
    expect(conforms("Connection", shaped)).toBe(true);
    expect(conforms("ConnectionDetail", { ...shaped, claims_detail: [toClaim(claim)] })).toBe(true);
  });

  it("claims carry a citation and the full terms they may be reused under", () => {
    const shaped = toClaim(claim);
    expect(shaped.citation).toEqual({
      source: "doi:10.1038/nature13186",
      doi: "10.1038/nature13186",
      pmid: null,
      pmcid: null,
      arxiv: null,
      locator: "Allen Mouse Brain Connectivity Atlas, experiment 1",
    });
    expect(shaped.terms).toEqual(TERMS["allen-institute"]);
    expect(shaped.terms.note).toMatch(/non-commercial/i);
    expect(conforms("Claim", shaped)).toBe(true);
    expect(toClaim({ ...claim, terms: "cc-by-4.0" }).terms.url).toBe("https://creativecommons.org/licenses/by/4.0/");
  });

  it("regions, region details and sources conform", () => {
    const region = { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus", atlas: "allen-mouse-ccf-2017", parent: "MBA:703", uberon: "UBERON:0006107", uberon_label: "basolateral amygdaloid nuclear complex", amygdala: true };
    expect(conforms("Region", toRegion(region))).toBe(true);
    const detail = regionDetail({
      region,
      children: [{ id: "MBA:303", acronym: "BLAa", name: "Basolateral amygdalar nucleus, anterior part" }],
      outputs: [{ id: edge.id, source: "MBA:295", target: "MBA:672", density: 0.42, claims: 2, accepted: 1 }],
      inputs: [],
      names: { "MBA:672": { id: "MBA:672", acronym: "CP", name: "Caudoputamen" } },
    });
    expect(detail.outputs[0]).toEqual({ connection: edge.id, region: { id: "MBA:672", acronym: "CP", name: "Caudoputamen" }, density: 0.42, claims: 2, accepted: 1 });
    expect(conforms("RegionDetail", detail)).toBe(true);
    const source: Source = { id: "doi:10.1038/nature13186", title: "A mesoscale connectome of the mouse brain", year: 2014, journal: "Nature", license: null, open_access: false, retracted: false };
    expect(conforms("Source", toSource(source))).toBe(true);
  });
});

describe("paging", () => {
  it("defaults, and accepts values in range", () => {
    expect(paging(new URLSearchParams())).toEqual({ limit: 50, offset: 0 });
    expect(paging(new URLSearchParams("limit=200&offset=400"))).toEqual({ limit: 200, offset: 400 });
  });

  it.each(["limit=0", "limit=201", "limit=x", "offset=-1", "offset=1.5"])("rejects %s", (query) => {
    expect(() => paging(new URLSearchParams(query))).toThrow(/limit|offset/);
  });
});
