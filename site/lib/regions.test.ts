import { describe, expect, it } from "vitest";

import { regionLabel } from "./regions";

const regions = {
  "MBA:295": { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus" },
};

describe("regionLabel", () => {
  it("names a known region by acronym and name", () => {
    expect(regionLabel("MBA:295", regions)).toEqual({ short: "BLA", long: "Basolateral amygdalar nucleus", id: "MBA:295" });
  });

  it("falls back to the ID for regions the atlas tables don't hold (UBERON, neuron types)", () => {
    expect(regionLabel("UBERON:0002883", regions)).toEqual({ short: "UBERON:0002883", long: null, id: "UBERON:0002883" });
  });
});
