import { describe, expect, it } from "vitest";

import { arcMidpoint, arcWidth, brainEdges } from "./brain";

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
      { id: "e1", source: "MBA:295", target: "MBA:672", density: 0.5, claims: 2, accepted: 1 },
      { id: "e2", source: "MBA:295", target: "MBA:536", density: null, claims: 1, accepted: 1 },
    ]);
  });

  it("ignores other measurements and claims of connections it wasn't given", () => {
    const other = { ...claim("MBA:295", "MBA:672", null), measurements: [{ quantity: "synapse_count", value: 9, unit: "1" }] };
    expect(brainEdges([edge("e1", "MBA:295", "MBA:672")], [other, claim("MBA:1", "MBA:2", 0.9)])).toEqual([
      { id: "e1", source: "MBA:295", target: "MBA:672", density: null, claims: 1, accepted: 1 },
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
