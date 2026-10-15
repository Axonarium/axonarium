import { describe, expect, it } from "vitest";

import {
  arcMidpoint,
  arcWidth,
  brainEdges,
  brainGaps,
  byDensity,
  directed,
  gapEdge,
  hubOf,
  inModule,
  linkedModule,
  linkedView,
  moduleText,
  namedRegions,
  networkData,
} from "./brain";

const edge = (id: string, subject: string, object: string) => ({ id, subject_id: subject, object_id: object });
const claim = (subject: string, object: string, density: number | null, status = "accepted") => ({
  subject_id: subject,
  object_id: object,
  status,
  measurements: density === null ? null : [{ quantity: "projection_density", value: density, unit: "1" }],
});

describe("brainEdges", () => {
  it("takes each connection's strongest density and counts its claims", () => {
    const found = brainEdges(
      [edge("e1", "MBA:295", "MBA:672"), edge("e2", "MBA:295", "MBA:536")],
      [
        claim("MBA:295", "MBA:672", 0.2),
        claim("MBA:295", "MBA:672", 0.5, "proposed"),
        claim("MBA:295", "MBA:536", null),
      ],
    );
    expect(found).toEqual([
      { id: "e1", source: "MBA:295", target: "MBA:672", density: 0.5, claims: 2, accepted: 1, papers: 0 },
      { id: "e2", source: "MBA:295", target: "MBA:536", density: null, claims: 1, accepted: 1, papers: 0 },
    ]);
  });

  it("counts the claims drafted from papers, which Allen's terms don't cover", () => {
    const fromPaper = { ...claim("MBA:295", "MBA:672", null, "proposed"), terms: "cc-by-4.0" };
    const fromAllen = { ...claim("MBA:295", "MBA:672", 0.3), terms: "allen-institute" };
    expect(brainEdges([edge("e1", "MBA:295", "MBA:672")], [fromPaper, fromAllen, claim("MBA:295", "MBA:672", 0.1)])).toEqual([
      { id: "e1", source: "MBA:295", target: "MBA:672", density: 0.3, claims: 3, accepted: 2, papers: 1 },
    ]);
  });

  it("ignores other measurements and claims of connections it wasn't given", () => {
    const other = { ...claim("MBA:295", "MBA:672", null), measurements: [{ quantity: "synapse_count", value: 9, unit: "1" }] };
    expect(brainEdges([edge("e1", "MBA:295", "MBA:672")], [other, claim("MBA:1", "MBA:2", 0.9)])).toEqual([
      { id: "e1", source: "MBA:295", target: "MBA:672", density: null, claims: 1, accepted: 1, papers: 0 },
    ]);
  });
});

describe("arcs", () => {
  it("lift the midpoint above both ends, more for longer arcs", () => {
    const short = arcMidpoint([0, 0, 0], [2, 0, 0]);
    const long = arcMidpoint([0, 0, 0], [8, 0, 0]);
    expect(short[0]).toBe(1);
    expect(short[1]).toBeGreaterThan(0);
    expect(long[1]).toBeGreaterThan(short[1]);
  });

  it("are wider for denser projections, and thin without a density", () => {
    expect(arcWidth(1, 1)).toBeGreaterThan(arcWidth(0.1, 1));
    expect(arcWidth(null, 1)).toBe(arcWidth(0, 1));
  });
});

describe("byDensity", () => {
  const at = (id: string, density: number | null) => ({ id, source: "MBA:295", target: id, density, claims: 1, accepted: 1, papers: 0 });
  const edges = [at("weak", 0.02), at("unstated", null), at("strong", 0.4), at("zero", 0)];

  it("keeps connections that state no density, whatever the minimum", () => {
    expect(byDensity(edges, 0.05).map((e) => e.id)).toEqual(["strong", "unstated"]);
    expect(byDensity(edges, 0).map((e) => e.id)).toEqual(["strong", "weak", "zero", "unstated"]);
  });

  it("lists the strongest first and connections without a density last", () => {
    expect(byDensity([at("a", null), at("b", 0.1), at("c", null), at("d", 0.3)], 0).map((e) => e.id)).toEqual(["d", "b", "a", "c"]);
  });
});

describe("networkData", () => {
  const region = (acronym: string) => ({ acronym, name: acronym, file: "", centroid: [0, 0, 0] as [number, number, number] });
  const regions = { "MBA:295": region("BLA"), "MBA:536": region("CEA"), "MBA:672": region("CP") };
  const shown = [
    { id: "e1", source: "MBA:295", target: "MBA:672", density: 0.5, claims: 1, accepted: 1, papers: 0 },
    { id: "e2", source: "MBA:295", target: "MBA:536", density: 0.2, claims: 1, accepted: 0, papers: 0 },
    { id: "e3", source: "MBA:536", target: "MBA:672", density: 0.1, claims: 1, accepted: 1, papers: 0 },
  ];

  it("makes one node per region, marking injected regions and counting inputs", () => {
    const { nodes } = networkData(shown, regions, ["MBA:295", "MBA:536"]);
    expect(nodes).toEqual([
      { id: "MBA:295", acronym: "BLA", name: "BLA", injected: true, inputs: 0 },
      { id: "MBA:536", acronym: "CEA", name: "CEA", injected: true, inputs: 1 },
      { id: "MBA:672", acronym: "CP", name: "CP", injected: false, inputs: 2 },
    ]);
  });

  it("makes fresh link objects for each call, since the graph library rewrites them", () => {
    const first = networkData(shown, regions, ["MBA:295"]);
    const second = networkData(shown, regions, ["MBA:295"]);
    expect(networkData(shown, regions, ["MBA:672"], (e) => e.target).links[0].from).toBe("MBA:672");
    expect(first.links).toEqual(second.links);
    expect(first.links[0]).not.toBe(second.links[0]);
    expect(first.links[0]).toEqual({ id: "e1", source: "MBA:295", target: "MBA:672", from: "MBA:295", density: 0.5, accepted: 1 });
  });
});

describe("directed", () => {
  const region = (amygdala: boolean) => ({ acronym: "", name: "", file: "", centroid: [0, 0, 0] as [number, number, number], amygdala });
  const regions = { "MBA:295": region(true), "MBA:536": region(true), "MBA:972": region(false), "MBA:672": region(false) };
  const e = (id: string, source: string, target: string) => ({ id, source, target, density: 0.1, claims: 1, accepted: 1, papers: 0 });
  const edges = [e("out", "MBA:295", "MBA:672"), e("within", "MBA:295", "MBA:536"), e("in", "MBA:972", "MBA:295"), e("off", "MBA:972", "MBA:1")];

  it("splits connections into the amygdala's outputs and its inputs from outside it", () => {
    expect(directed(edges, regions, "outputs").map((x) => x.id)).toEqual(["out", "within"]);
    expect(directed(edges, regions, "inputs").map((x) => x.id)).toEqual(["in"]);
  });

  it("names the amygdala end of each", () => {
    expect(hubOf(edges[0], "outputs")).toBe("MBA:295");
    expect(hubOf(edges[2], "inputs")).toBe("MBA:295");
  });
});

describe("modules", () => {
  const region = (modules?: string[], amygdala = false) => ({ acronym: "", name: "", file: "", centroid: [0, 0, 0] as [number, number, number], amygdala, modules });
  // BLA (amygdala) projects to PL (prefrontal) and CP (no module); CA1 (hippocampus) projects to PL.
  const regions = { "MBA:295": region(["amygdala"], true), "MBA:972": region(["prefrontal"]), "MBA:382": region(["hippocampus"]), "MBA:672": region([]) };
  const e = (id: string, source: string, target: string) => ({ id, source, target, density: 0.1, claims: 1, accepted: 1, papers: 0 });
  const edges = [e("bla-pl", "MBA:295", "MBA:972"), e("bla-cp", "MBA:295", "MBA:672"), e("ca1-pl", "MBA:382", "MBA:972")];
  const MODULES = [{ id: "amygdala", name: "Amygdala" }, { id: "hippocampus", name: "Hippocampal formation" }, { id: "prefrontal", name: "Prefrontal cortex" }];

  it("place a region by its modules, or by the amygdala flag in meshes exported before them", () => {
    expect(inModule(regions["MBA:972"], "prefrontal")).toBe(true);
    expect(inModule(regions["MBA:295"], "prefrontal")).toBe(false);
    expect(inModule(region(undefined, true), "amygdala")).toBe(true);
    expect(inModule(region(undefined, true), "hippocampus")).toBe(false);
    expect(inModule(undefined, "amygdala")).toBe(false);
  });

  it("decide which end of a connection is the hub", () => {
    expect(directed(edges, regions, "outputs", "prefrontal")).toEqual([]);
    expect(directed(edges, regions, "inputs", "prefrontal").map((x) => x.id)).toEqual(["bla-pl", "ca1-pl"]);
    expect(directed(edges, regions, "outputs", "hippocampus").map((x) => x.id)).toEqual(["ca1-pl"]);
    expect(directed(edges, regions, "outputs").map((x) => x.id)).toEqual(["bla-pl", "bla-cp"]); // the amygdala by default
  });

  it("open a linked region in its own module first, else the first where a connection names it", () => {
    expect(linkedModule(edges, regions, "MBA:972", MODULES)).toBe("prefrontal");
    expect(linkedView(edges, regions, "MBA:972", "prefrontal")).toEqual({ direction: "inputs", source: "MBA:972" });
    expect(linkedModule(edges, regions, "MBA:672", MODULES)).toBe("amygdala");
    expect(linkedModule(edges, regions, "MBA:1", MODULES)).toBeNull();
  });

  it("read as part of a sentence", () => {
    expect(moduleText(MODULES[1])).toBe("the hippocampal formation");
  });

  it("place a species's UBERON terms by the terms each module resolves to, named as the site names them", () => {
    const names = {
      "UBERON:0006107": { id: "UBERON:0006107", acronym: "BLA", name: "basolateral amygdaloid nuclear complex", kind: "uberon" as const },
      "UBERON:0002421": { id: "UBERON:0002421", acronym: null, name: "hippocampal formation", kind: "uberon" as const },
    };
    const terms = [{ id: "amygdala", terms: ["UBERON:0006107"] }, { id: "hippocampus", terms: ["UBERON:0002421"] }];
    expect(namedRegions(["UBERON:0006107", "UBERON:0002421", "UBERON:0001945"], names, terms)).toEqual({
      "UBERON:0006107": { acronym: "BLA", name: "basolateral amygdaloid nuclear complex", file: "", centroid: [0, 0, 0], modules: ["amygdala"] },
      "UBERON:0002421": { acronym: "hippocampal formation", name: "hippocampal formation", file: "", centroid: [0, 0, 0], modules: ["hippocampus"] },
      "UBERON:0001945": { acronym: "UBERON:0001945", name: "UBERON:0001945", file: "", centroid: [0, 0, 0], modules: [] },
    });
  });
});

describe("linkedView", () => {
  const region = (amygdala: boolean) => ({ acronym: "", name: "", file: "", centroid: [0, 0, 0] as [number, number, number], amygdala });
  const regions = { "MBA:295": region(true), "MBA:131": region(true), "MBA:972": region(false), "MBA:672": region(false) };
  const e = (id: string, source: string, target: string) => ({ id, source, target, density: 0.1, claims: 1, accepted: 1, papers: 0 });
  // BLA has injections; LA (amygdala) is only a target; PL only sends; CP only receives.
  const edges = [e("1", "MBA:295", "MBA:672"), e("2", "MBA:972", "MBA:131"), e("3", "MBA:295", "MBA:131")];

  it("opens an amygdala region with injections on its outputs", () => {
    expect(linkedView(edges, regions, "MBA:295")).toEqual({ direction: "outputs", source: "MBA:295" });
  });

  it("opens an amygdala region without injections on its inputs", () => {
    expect(linkedView(edges, regions, "MBA:131")).toEqual({ direction: "inputs", source: "MBA:131" });
  });

  it("selects other regions in the direction they appear", () => {
    expect(linkedView(edges, regions, "MBA:672")).toEqual({ direction: "outputs", selected: "MBA:672" });
    expect(linkedView(edges, regions, "MBA:972")).toEqual({ direction: "inputs", selected: "MBA:972" });
    expect(linkedView(edges, regions, "MBA:1")).toBeNull();
  });
});

describe("gaps", () => {
  const [gap] = brainGaps([
    {
      id: "MBA:4|projects_to|MBA:10|NCBITaxon:10090",
      subject_id: "MBA:4",
      object_id: "MBA:10",
      density: 0.3,
      suggested_by: ["MBA:2|projects_to|MBA:10|NCBITaxon:10090", "MBA:31|projects_to|MBA:10|NCBITaxon:10090"],
    },
  ]);

  it("keeps each suggesting connection's region", () => {
    expect(gap).toEqual({ id: "MBA:4|projects_to|MBA:10|NCBITaxon:10090", source: "MBA:4", target: "MBA:10", density: 0.3, by: ["MBA:2", "MBA:31"] });
  });

  it("draws as a connection without claims, so dashed", () => {
    expect(gapEdge(gap)).toEqual({ id: gap.id, source: "MBA:4", target: "MBA:10", density: 0.3, claims: 0, accepted: 0, papers: 0 });
  });
});
