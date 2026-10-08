import { describe, expect, it } from "vitest";

import {
  checkedBy,
  checkNote,
  citationLinks,
  citedAs,
  citationParts,
  edgeFromParam,
  edgeHref,
  formatMeasurement,
  madeBy,
  namesInPaper,
  pageParam,
  predicateLabel,
  proposedBecause,
  regionHref,
  sourceHref,
  speciesName,
  strongestFirst,
  withParam,
} from "./format";

describe("citationLinks", () => {
  it("links every identifier a citation carries, DOI first", () => {
    expect(
      citationLinks({ doi: "10.1038/s41467-021-22915-5", pmid: "34001873", pmcid: "PMC8129205", arxiv: null }),
    ).toEqual([
      { label: "DOI 10.1038/s41467-021-22915-5", href: "https://doi.org/10.1038/s41467-021-22915-5" },
      { label: "PubMed 34001873", href: "https://pubmed.ncbi.nlm.nih.gov/34001873/" },
      { label: "PMC8129205", href: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8129205/" },
    ]);
  });

  it("escapes DOIs with characters that break URLs", () => {
    expect(citationLinks({ doi: "10.1002/(sici)1096<1::aid>3.0.co;2-#" })[0].href).toBe(
      "https://doi.org/10.1002/(sici)1096%3C1%3A%3Aaid%3E3.0.co%3B2-%23",
    );
  });

  it("links arXiv preprints", () => {
    expect(citationLinks({ arxiv: "2409.13740" })).toEqual([
      { label: "arXiv 2409.13740", href: "https://arxiv.org/abs/2409.13740" },
    ]);
  });
});

describe("labels", () => {
  it("names the project's species and passes others through", () => {
    expect(speciesName("NCBITaxon:10090")).toBe("Mouse");
    expect(speciesName("NCBITaxon:10116")).toBe("Rat");
    expect(speciesName("NCBITaxon:9606")).toBe("Human");
    expect(speciesName("NCBITaxon:9544")).toBe("NCBITaxon:9544");
  });

  it("spells predicates out", () => {
    expect(predicateLabel("projects_to")).toBe("projects to");
    expect(predicateLabel("functionally_connects_to")).toBe("functionally connects to");
  });
});

describe("edge URLs", () => {
  const id = "MBA:295|projects_to|MBA:559|NCBITaxon:10090";

  it("round-trips an edge ID through its URL segment", () => {
    const segment = edgeHref(id).replace("/edges/", "");
    expect(segment).not.toMatch(/[|:]/);
    expect(edgeFromParam(segment)).toBe(id);
  });

  it("accepts a segment the framework already decoded", () => {
    expect(edgeFromParam(id)).toBe(id);
  });
});

describe("measurements", () => {
  it("leaves out uncertainty that is null or missing", () => {
    expect(formatMeasurement({ quantity: "projection_density", value: 0.12, unit: "1", sd: null, n: null })).toBe(
      "projection density: 0.12",
    );
  });

  it("shows SD, SEM, the confidence interval and n", () => {
    expect(
      formatMeasurement({ quantity: "conduction_delay", value: 4.5, unit: "ms", sem: 0.3, ci_low: 3.9, ci_high: 5.1, n: 12 }),
    ).toBe("conduction delay: 4.5 ms (SEM 0.3; CI 3.9–5.1), n = 12");
    expect(formatMeasurement({ quantity: "synapse_count", value: 40, unit: "1", sd: 6 })).toBe("synapse count: 40 (SD 6)");
  });
});

describe("filter URLs", () => {
  it("sets, replaces and removes one parameter, keeping the others", () => {
    const params = new URLSearchParams("species=NCBITaxon%3A10090&predicate=projects_to");
    expect(withParam("/explore", params, "predicate", "synapses_onto")).toBe(
      "/explore?species=NCBITaxon%3A10090&predicate=synapses_onto",
    );
    expect(withParam("/explore", params, "species", "")).toBe("/explore?predicate=projects_to");
    expect(withParam("/explore", new URLSearchParams("species=x"), "species", "")).toBe("/explore");
  });
});

describe("citationParts", () => {
  it("splits an atlas citation into its text and its link", () => {
    expect(citationParts("Wang et al. 2020, https://doi.org/10.1016/j.cell.2020.04.007")).toEqual({
      text: "Wang et al. 2020",
      href: "https://doi.org/10.1016/j.cell.2020.04.007",
    });
    expect(citationParts("unpublished")).toEqual({ text: "unpublished", href: null });
  });
});

describe("region URLs", () => {
  it("make one segment of a region ID that edgeFromParam reads back", () => {
    expect(regionHref("MBA:295")).toBe("/regions/MBA%3A295");
    expect(edgeFromParam("MBA%3A295")).toBe("MBA:295");
    expect(edgeFromParam("MBA:295")).toBe("MBA:295");
  });
});

describe("strongestFirst", () => {
  it("puts the densest connections first and those without a density last", () => {
    const edges = [{ id: "c", density: null }, { id: "b", density: 0.1 }, { id: "a", density: 0.5 }, { id: "d", density: 0.1 }];
    expect(edges.sort(strongestFirst).map((e) => e.id)).toEqual(["a", "b", "d", "c"]);
  });
});

describe("provenance", () => {
  const extracted = {
    curation: { by: "agent", role: "extractor", model: "claude-opus-5-5", prompt: "extract@0.2.0" },
    verification: { by: "agent", model: "claude-opus-5-5", verdict: "disagree" },
    status: "proposed",
    extra: { "extract.subject_name": "BLA complex", "extract.object_name": "CeA", "verify.note": "The paper traced the reverse direction." },
  };
  const allen = { curation: { by: "agent", role: "ingester", model: "deterministic-adapter", prompt: "allen-connectivity@1.3.0" }, status: "proposed", extra: { "allen.experiment": 1 } };

  it("says who made a claim and who checked it", () => {
    expect(madeBy(extracted)).toBe("an AI model reading the paper (claude-opus-5-5, extract@0.2.0)");
    expect(madeBy(allen)).toBe("an adapter reading a database (allen-connectivity@1.3.0)");
    expect(madeBy({ curation: { by: "human", role: "curator", orcid: "0000-0002-1825-0097" }, status: "accepted" })).toBe("a curator (ORCID 0000-0002-1825-0097)");
    expect(checkedBy(extracted)).toBe("a second AI model (claude-opus-5-5) disagrees");
    expect(checkedBy(allen)).toBeNull();
    expect(checkNote(extracted)).toBe("The paper traced the reverse direction.");
    expect(namesInPaper(extracted)).toEqual(["BLA complex", "CeA"]);
    expect(namesInPaper(allen)).toBeNull();
  });

  it("explains why a claim is still proposed", () => {
    expect(proposedBecause(extracted)).toMatch(/^Drafted and checked by AI models/);
    expect(proposedBecause(allen)).toBe("Most of the injected tracer landed outside the region it names.");
    expect(proposedBecause({ ...allen, status: "accepted" })).toBeNull();
  });
});

describe("sources", () => {
  it("link to their page and cite the identifier their key holds", () => {
    expect(sourceHref("doi:10.1002/cne.23960")).toBe("/sources/doi%3A10.1002%2Fcne.23960");
    expect(citedAs("doi:10.1002/cne.23960")).toEqual({ doi: "10.1002/cne.23960" });
    expect(citedAs("pubmed:26779765")).toEqual({ pmid: "26779765" });
    expect(citedAs("pmc:PMC4900924")).toEqual({ pmcid: "PMC4900924" });
    expect(citedAs("arxiv:2101.00001")).toEqual({ arxiv: "2101.00001" });
    expect(citedAs("isbn:123")).toEqual({});
  });

  it("read the page number from the URL, 1 or more", () => {
    expect([pageParam("3"), pageParam("0"), pageParam("x"), pageParam(undefined), pageParam(["2"])]).toEqual([3, 1, 1, 1, 1]);
  });
});
