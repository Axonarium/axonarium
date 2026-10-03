import { describe, expect, it } from "vitest";

import { citationLinks, edgeFromParam, edgeHref, predicateLabel, speciesName } from "./format";

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
