import { describe, expect, it } from "vitest";

import { regionIndex } from "./region-index";

describe("regionIndex", () => {
  it("counts each region's outputs and inputs, amygdala first, then by acronym", () => {
    const edges = [
      { subject_id: "MBA:295", object_id: "MBA:672" },
      { subject_id: "MBA:295", object_id: "MBA:31" },
      { subject_id: "MBA:31", object_id: "MBA:295" },
      { subject_id: "UBERON:1", object_id: "MBA:295" },
    ];
    const names = {
      "MBA:295": { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus", amygdala: true },
      "MBA:672": { id: "MBA:672", acronym: "CP", name: "Caudoputamen", amygdala: false },
      "MBA:31": { id: "MBA:31", acronym: "ACA", name: "Anterior cingulate area", amygdala: false },
    };
    expect(regionIndex(edges, names)).toEqual([
      { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus", amygdala: true, outputs: 2, inputs: 2 },
      { id: "MBA:31", acronym: "ACA", name: "Anterior cingulate area", amygdala: false, outputs: 1, inputs: 1 },
      { id: "MBA:672", acronym: "CP", name: "Caudoputamen", amygdala: false, outputs: 0, inputs: 1 },
    ]);
  });
});
