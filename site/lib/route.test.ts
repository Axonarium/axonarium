import { describe, expect, it } from "vitest";

import type { BrainEdge } from "./brain";
import { reachable, shortestRoute } from "./route";

const edge = (source: string, target: string, density: number | null): BrainEdge => ({
  id: `${source}|projects_to|${target}`, source, target, density, claims: 1, accepted: 1,
});
const path = (hops: BrainEdge[] | null) => hops && [hops[0].source, ...hops.map((h) => h.target)].join(" → ");

// PL reaches CEA directly (weakly) or through BLA; LA reaches CEA through BLA or BMA, and its weakest
// hop is stronger through BLA.
const EDGES = [
  edge("PL", "BLA", 0.3),
  edge("BLA", "CEA", 0.4),
  edge("PL", "CEA", 0.02),
  edge("LA", "BLA", 0.5),
  edge("LA", "BMA", 0.2),
  edge("BMA", "CEA", 0.6),
  edge("CEA", "PAG", null),
  edge("PAG", "PAG", 0.9),
];

describe("shortestRoute", () => {
  it("takes the fewest hops, however weak", () => {
    expect(path(shortestRoute(EDGES, "PL", "CEA"))).toBe("PL → CEA");
  });

  it("among routes with as few hops, takes the one whose weakest hop is strongest", () => {
    // LA → BLA → CEA's weakest hop is 0.4; LA → BMA → CEA's is 0.2.
    expect(path(shortestRoute(EDGES, "LA", "CEA"))).toBe("LA → BLA → CEA");
    const swapped = EDGES.map((e) => (e.source === "LA" && e.target === "BMA" ? edge("LA", "BMA", 0.45) : e));
    expect(path(shortestRoute(swapped, "LA", "CEA"))).toBe("LA → BMA → CEA");
  });

  it("follows the direction of connections, and crosses hops without a density", () => {
    expect(path(shortestRoute(EDGES, "LA", "PAG"))).toBe("LA → BLA → CEA → PAG");
    expect(shortestRoute(EDGES, "CEA", "BLA")).toBeNull();
  });

  it("finds no route to the start or between unknown regions", () => {
    expect(shortestRoute(EDGES, "PL", "PL")).toBeNull();
    expect(shortestRoute(EDGES, "X", "CEA")).toBeNull();
  });

  it("returns each hop's own connection", () => {
    const hops = shortestRoute(EDGES, "PL", "PAG")!;
    expect(hops.map((h) => h.id)).toEqual(["PL|projects_to|CEA", "CEA|projects_to|PAG"]);
  });
});

describe("reachable", () => {
  it("lists every region downstream, not the start, ignoring self-connections", () => {
    expect([...reachable(EDGES, "LA")].sort()).toEqual(["BLA", "BMA", "CEA", "PAG"]);
    expect([...reachable(EDGES, "PAG")]).toEqual([]);
  });
});
