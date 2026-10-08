import { describe, expect, it } from "vitest";

import { type MappedRegion, regionLabel, uberonNames } from "./regions";

const regions = {
  "MBA:295": { id: "MBA:295", acronym: "BLA", name: "Basolateral amygdalar nucleus" },
  "UBERON:0002430": { id: "UBERON:0002430", acronym: "LHA", name: "Lateral hypothalamic area", kind: "uberon" as const },
  "nt-3kvfdzf7wn": { id: "nt-3kvfdzf7wn", acronym: null, name: "MEA glutamatergic neurons", kind: "neuron_type" as const },
};

describe("regionLabel", () => {
  it("names a known region by acronym and name, linking to its page", () => {
    expect(regionLabel("MBA:295", regions)).toEqual({ short: "BLA", long: "Basolateral amygdalar nucleus", id: "MBA:295", href: "/regions/MBA%3A295" });
  });

  it("names UBERON terms and neuron types without a page to link to", () => {
    expect(regionLabel("UBERON:0002430", regions)).toEqual({ short: "LHA", long: "Lateral hypothalamic area", id: "UBERON:0002430", href: null });
    expect(regionLabel("nt-3kvfdzf7wn", regions)).toEqual({
      short: "MEA glutamatergic neurons", long: "MEA glutamatergic neurons", id: "nt-3kvfdzf7wn", href: null,
    });
  });

  it("falls back to the ID for anything it has no name for", () => {
    expect(regionLabel("UBERON:0002883", regions)).toEqual({ short: "UBERON:0002883", long: null, id: "UBERON:0002883", href: null });
  });
});

describe("uberonNames", () => {
  const mapped = (id: string, acronym: string, name: string, extra: Partial<MappedRegion> = {}): MappedRegion => ({
    id, acronym, name, atlas: "allen-mouse-ccf-2017", parent: null, uberon: null, uberon_label: null, ...extra,
  });
  const rows = [
    mapped("MBA:295", "BLA", "Basolateral amygdalar nucleus", { uberon: "UBERON:0002887", uberon_label: "basal amygdaloid nucleus" }),
    mapped("MBA:303", "BLAa", "Basolateral amygdalar nucleus, anterior part", { uberon: "UBERON:0002887", parent: "MBA:295" }),
    mapped("WHS:100", "LH", "lateral hypothalamus", { uberon: "UBERON:0002430", atlas: "waxholm-sd-rat-v4" }),
    mapped("MBA:194", "LHA", "Lateral hypothalamic area", { uberon: "UBERON:0002430" }),
    mapped("MBA:290", "HY-x", "A subdivision", { uberon: "UBERON:0002430", parent: "MBA:194" }),
  ];

  it("takes the term's own label, else the highest mapped region of the Allen mouse atlas", () => {
    expect(uberonNames(["UBERON:0002887", "UBERON:0002430", "UBERON:9999999"], rows)).toEqual({
      "UBERON:0002887": { id: "UBERON:0002887", acronym: "BLA", name: "basal amygdaloid nucleus", kind: "uberon" },
      "UBERON:0002430": { id: "UBERON:0002430", acronym: "LHA", name: "Lateral hypothalamic area", kind: "uberon" },
    });
  });

  it("gives no acronym when several regions map to the term", () => {
    const two = [mapped("MBA:1", "LA", "Lateral amygdalar nucleus", { uberon: "UBERON:1" }), mapped("MBA:2", "BLA", "Basolateral", { uberon: "UBERON:1" })];
    expect(uberonNames(["UBERON:1"], two)).toEqual({ "UBERON:1": { id: "UBERON:1", acronym: null, name: "Lateral amygdalar nucleus", kind: "uberon" } });
  });

  it("uses another atlas when the mouse atlas maps nothing to the term", () => {
    expect(uberonNames(["UBERON:0002430"], rows.slice(2, 3))["UBERON:0002430"]?.name).toBe("lateral hypothalamus");
  });
});
