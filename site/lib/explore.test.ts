import { describe, expect, it } from "vitest";

import { exploreHref, exploreState, pageCount } from "./explore";

const FACETS = { species: ["NCBITaxon:10090", "NCBITaxon:10116"], predicate: ["projects_to"] };

describe("the explore page's URL", () => {
  it("keeps only filters the connections have, and a page of 1 or more", () => {
    expect(exploreState({ species: "NCBITaxon:10116", predicate: "projects_to", page: "3" }, FACETS)).toEqual({
      species: "NCBITaxon:10116",
      predicate: "projects_to",
      page: 3,
    });
    expect(exploreState({ species: "x</style>", predicate: ["projects_to", "x"], page: "-2" }, FACETS)).toEqual({
      species: "",
      predicate: "",
      page: 1,
    });
    expect(exploreState({ page: "abc" }, FACETS).page).toBe(1);
  });

  it("round-trips, leaving out defaults", () => {
    expect(exploreHref({ species: "", predicate: "", page: 1 })).toBe("/explore");
    const state = { species: "NCBITaxon:10090", predicate: "projects_to", page: 2 };
    expect(exploreHref(state)).toBe("/explore?species=NCBITaxon%3A10090&predicate=projects_to&page=2");
    expect(exploreState(Object.fromEntries(new URL(exploreHref(state), "http://x").searchParams), FACETS)).toEqual(state);
  });

  it("counts pages of 100, at least one", () => {
    expect([pageCount(0), pageCount(100), pageCount(101), pageCount(1039)]).toEqual([1, 1, 2, 11]);
  });
});
