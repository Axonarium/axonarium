import { describe, expect, it } from "vitest";

import { regionIndex } from "./region-index";

describe("regionIndex", () => {
  it("counts each region's outputs and inputs, the amygdala's first, then by acronym", () => {
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
      { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus", amygdala: true, modules: ["amygdala"], outputs: 2, inputs: 2 },
      { id: "MBA:31", acronym: "ACA", name: "Anterior cingulate area", amygdala: false, modules: [], outputs: 1, inputs: 1 },
      { id: "MBA:672", acronym: "CP", name: "Caudoputamen", amygdala: false, modules: [], outputs: 0, inputs: 1 },
    ]);
  });

  it("puts the modules' regions first, in the modules' order", () => {
    const edges = [
      { subject_id: "MBA:672", object_id: "MBA:31" },
      { subject_id: "MBA:382", object_id: "MBA:295" },
    ];
    const name = (id: string, acronym: string, modules: string[] | null) => ({ id, acronym, name: acronym, amygdala: modules?.includes("amygdala"), modules });
    const names = {
      "MBA:295": name("MBA:295", "BLA", ["amygdala"]),
      "MBA:31": name("MBA:31", "ACA", ["prefrontal"]),
      "MBA:382": name("MBA:382", "CA1", ["hippocampus"]),
      "MBA:672": name("MBA:672", "CP", null),
    };
    expect(regionIndex(edges, names, ["amygdala", "hippocampus", "prefrontal"]).map((r) => r.acronym)).toEqual(["BLA", "CA1", "ACA", "CP"]);
  });
});
