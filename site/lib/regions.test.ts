import { describe, expect, it } from "vitest";

import { AMYGDALA, amygdalaRegions, regionLabel } from "./regions";

const regions = {
  "MBA:295": { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus", atlas: "allen-mouse-ccf-2017", uberon: "UBERON:0002887" },
  "MBA:536": { id: "MBA:536", acronym: "CEA", name: "Central amygdalar nucleus", atlas: "allen-mouse-ccf-2017", uberon: "UBERON:0002883" },
  "MBA:8": { id: "MBA:8", acronym: "grey", name: "Basic cell groups and regions", atlas: "allen-mouse-ccf-2017", uberon: null },
};

describe("regionLabel", () => {
  it("names a known region by acronym and name", () => {
    expect(regionLabel("MBA:295", regions)).toEqual({ short: "BLA", long: "Basolateral amygdalar nucleus", id: "MBA:295" });
  });

  it("falls back to the ID for regions the atlas tables don't hold (UBERON, neuron types)", () => {
    expect(regionLabel("UBERON:0002883", regions)).toEqual({ short: "UBERON:0002883", long: null, id: "UBERON:0002883" });
  });
});

describe("amygdalaRegions", () => {
  it("keeps an atlas's amygdala regions, in the order of AMYGDALA (basal before central)", () => {
    expect(amygdalaRegions(Object.values(regions)).map((r) => r.acronym)).toEqual(["BLA", "CEA"]);
    expect(AMYGDALA[0]).toEqual({ uberon: "UBERON:0001876", label: "amygdala" });
  });
});
