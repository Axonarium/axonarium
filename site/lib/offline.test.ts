import { describe, expect, it } from "vitest";

import * as offline from "./offline";
import type { Tables } from "./offline";
import type { ConnectivityClaim, Edge } from "./types";

const ATLAS = "allen-mouse-ccf-2017";
const region = (id: string, acronym: string, name: string, extra: Partial<Tables["regions"][number]> = {}) => ({
  id, acronym, name, atlas: ATLAS, parent: null, uberon: null, uberon_label: null, amygdala: false, synonyms: null, extra: null, ...extra,
});
const edge = (subject: string, object: string, density: number | null, extra: Partial<Edge> = {}): Edge => ({
  id: `${subject}|projects_to|${object}|NCBITaxon:10090`, subject_id: subject, subject_type: "region", predicate: "projects_to",
  object_id: object, object_type: "region", species: "NCBITaxon:10090", n_claims: 1, n_present: 1, n_absent: 0, n_ambiguous: 0,
  n_disputed: 0, evidence_classes: ["anterograde_tracer"], strength: null, signs: ["unknown"], claim_ids: [], density, terms: ["allen-institute"],
  ...extra,
});
const claim = (id: string, subject: string, object: string, density: number | null, extra: Partial<ConnectivityClaim> = {}): ConnectivityClaim => ({
  id, subject_type: "region", subject_id: subject, subject_atlas: ATLAS, predicate: "projects_to", object_type: "region", object_id: object,
  object_atlas: ATLAS, species: "NCBITaxon:10090", evidence_class: "anterograde_tracer", result: "present", sign: "unknown", strength: null,
  measurements: density === null ? null : [{ quantity: "projection_density", value: density, unit: "1" }], source_key: "doi:10.1038/nature13186",
  doi: "10.1038/nature13186", pmid: null, pmcid: null, arxiv: null, locator: "experiment 1", paraphrase: "p", excerpt: null,
  curation: { by: "agent", role: "ingester", date: "2026-10-03" }, verification: null, status: "accepted", extra: null, terms: "allen-institute",
  ...extra,
});

const tables: Tables = {
  atlases: [{ id: ATLAS, name: "Allen mouse", species: "NCBITaxon:10090", version: "2017", url: null, brainglobe_name: "allen_mouse_25um", citation: null, extra: null }],
  regions: [
    region("MBA:295", "BLA", "Basolateral amygdalar nucleus", { amygdala: true, parent: "MBA:319", uberon: "UBERON:0006107", uberon_label: "basolateral amygdaloid nuclear complex" }),
    region("MBA:319", "BLAa", "Basolateral amygdalar nucleus, anterior part", { amygdala: true }),
    region("MBA:672", "CP", "Caudoputamen"),
    region("MBA:536", "CEA", "Central amygdalar nucleus", { amygdala: true }),
    region("MBA:303", "BLAp", "Basolateral amygdalar nucleus, posterior part", { parent: "MBA:295", amygdala: true }),
  ],
  sources: [{ id: "doi:10.1038/nature13186", kind: "journal_article", title: "A mesoscale connectome", year: 2014, journal: "Nature", license: null, open_access: null, retracted: false }],
  connectivity_claims: [
    claim("clm-b", "MBA:295", "MBA:672", 0.4),
    claim("clm-a", "MBA:295", "MBA:672", 0.1, { status: "proposed" }),
    claim("clm-c", "MBA:295", "MBA:536", null),
    claim("clm-d", "MBA:672", "MBA:295", 0.05, { status: "retracted" }),
  ],
  homology_claims: [{}],
  edges: [edge("MBA:295", "MBA:672", 0.4), edge("MBA:295", "MBA:536", null), edge("MBA:672", "MBA:295", 0.05, { n_present: 0, species: "NCBITaxon:10116" })],
};

describe("the snapshot answers like the database", () => {
  it("counts claims, connections, sources and species", () => {
    expect(offline.counts(tables)).toEqual({ claims: 5, edges: 3, sources: 1, species: 2 });
  });

  it("lists connections by ID, with the summary columns only", () => {
    const listed = offline.edges(tables);
    expect(listed.map((e) => e.id)).toEqual([...tables.edges.map((e) => e.id)].sort());
    expect(Object.keys(listed[0]).sort()).toEqual(
      ["density", "id", "n_absent", "n_claims", "n_present", "object_id", "predicate", "species", "strength", "subject_id"],
    );
  });

  it("finds one connection, claim or source, or null", () => {
    expect(offline.edge(tables, tables.edges[0].id)).toBe(tables.edges[0]);
    expect(offline.edge(tables, "nope")).toBeNull();
    expect(offline.claim(tables, "clm-c")?.id).toBe("clm-c");
    expect(offline.claims(tables, ["clm-b", "clm-a", "clm-x"]).map((c) => c.id)).toEqual(["clm-a", "clm-b"]);
    expect(offline.source(tables, "doi:10.1038/nature13186")?.journal).toBe("Nature");
    expect(offline.source(tables, "doi:10.1/none")).toBeNull();
  });

  it("names regions, leaving out IDs that aren't regions", () => {
    expect(offline.regionNames(tables, ["MBA:295", "UBERON:0001876"])).toEqual({
      "MBA:295": { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus", amygdala: true },
    });
  });

  it("gives each atlas its region count and amygdala regions", () => {
    const [entry] = offline.atlases(tables);
    expect(entry.atlas).not.toHaveProperty("extra");
    expect(entry.regions).toBe(5);
    expect(entry.amygdala.map((r) => r.id)).toEqual(["MBA:295", "MBA:303", "MBA:319", "MBA:536"]);
  });

  it("draws the brain's connections from claims that found them, not retracted ones", () => {
    const drawn = offline.brain(tables, ATLAS);
    expect(drawn).toEqual([
      { id: tables.edges[1].id, source: "MBA:295", target: "MBA:536", density: null, claims: 1, accepted: 1 },
      { id: tables.edges[0].id, source: "MBA:295", target: "MBA:672", density: 0.4, claims: 2, accepted: 1 },
    ]);
    expect(offline.brain(tables, "waxholm-sd-rat-v4")).toEqual([]);
  });

  it("builds a region's page: subregions, outputs strongest first, inputs and names", () => {
    const page = offline.region(tables, "MBA:295");
    expect(page?.region).toEqual({
      id: "MBA:295", name: "Basolateral amygdalar nucleus", acronym: "BLA", atlas: ATLAS, parent: "MBA:319",
      uberon: "UBERON:0006107", uberon_label: "basolateral amygdaloid nuclear complex", amygdala: true,
    });
    expect(page?.children).toEqual([{ id: "MBA:303", acronym: "BLAp", name: "Basolateral amygdalar nucleus, posterior part" }]);
    expect(page?.outputs.map((e) => e.target)).toEqual(["MBA:672", "MBA:536"]);
    expect(page?.inputs).toEqual([]); // its one input found nothing (n_present 0)
    expect(Object.keys(page?.names ?? {}).sort()).toEqual(["MBA:319", "MBA:536", "MBA:672"]);
    expect(offline.region(tables, "MBA:1")).toBeNull();
  });

  it("pages regions, matching part of an acronym or name in any case", () => {
    expect(offline.regionsPage(tables, { q: "bla", limit: 2, offset: 0 })).toMatchObject({ total: 3, items: [{ id: "MBA:295" }, { id: "MBA:303" }] });
    expect(offline.regionsPage(tables, { q: "CAUDO", limit: 50, offset: 0 }).items.map((r) => r.id)).toEqual(["MBA:672"]);
    expect(offline.regionsPage(tables, { amygdala: false, limit: 50, offset: 0 }).total).toBe(1);
    expect(offline.regionsPage(tables, { q: "bla*,name.eq.x", limit: 50, offset: 0 }).total).toBe(0); // sanitised like the API
    expect(offline.regionsPage(tables, { atlas: "other", limit: 50, offset: 0 })).toEqual({ items: [], total: 0 });
  });

  it("pages connections, strongest first, those without a density last", () => {
    const all = offline.connectionsPage(tables, { limit: 50, offset: 0 });
    expect(all.items.map((e) => e.density)).toEqual([0.4, 0.05, null]);
    expect(offline.connectionsPage(tables, { minDensity: 0.1, limit: 50, offset: 0 }).items.map((e) => e.object_id)).toEqual(["MBA:672"]);
    expect(offline.connectionsPage(tables, { subject: "MBA:295", limit: 1, offset: 1 })).toMatchObject({ total: 2, items: [{ object_id: "MBA:536" }] });
    expect(offline.connectionsPage(tables, { species: "NCBITaxon:10116", limit: 50, offset: 0 }).total).toBe(1);
  });
});
