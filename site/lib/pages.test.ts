import { describe, expect, it } from "vitest";

import { fetchAll, PAGE } from "./pages";

describe("fetchAll", () => {
  it("asks for successive pages until one comes back short", async () => {
    const rows = Array.from({ length: 2 * PAGE + 5 }, (_, i) => i);
    const asked: [number, number][] = [];
    const all = await fetchAll(async (from, to) => {
      asked.push([from, to]);
      return rows.slice(from, to + 1);
    });
    expect(all).toEqual(rows);
    expect(asked).toEqual([
      [0, PAGE - 1],
      [PAGE, 2 * PAGE - 1],
      [2 * PAGE, 3 * PAGE - 1],
    ]);
  });

  it("stops after one request when everything fits", async () => {
    let calls = 0;
    expect(await fetchAll(async () => (calls++, [1, 2]))).toEqual([1, 2]);
    expect(calls).toBe(1);
  });
});
