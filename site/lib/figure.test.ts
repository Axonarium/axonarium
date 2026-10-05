import { describe, expect, it } from "vitest";

import { type FigureLink, type FigureNode, networkSvg, PLOT_BACKGROUND, wrap } from "./figure";

const node = (id: string, x: number, y: number, injected = false): FigureNode => ({
  id, acronym: id === "c" ? "A<B" : id.toUpperCase(), x, y, r: injected ? 7 : 3, color: injected ? "#f97316" : "#cbd5e1", injected,
});
const link = (source: string, target: string, dashed = false): FigureLink => ({ source, target, color: "#f97316", width: 2, dashed });
const TEXT = {
  title: "Where the mouse amygdala projects",
  subtitle: "BLA; projection density ≥ 0.05; 2 connections",
  legend: [{ label: "BLA", color: "#f97316" }],
  caption: ["Data: Allen Mouse Brain Connectivity Atlas (Oh et al. 2014), © Allen Institute", "Figure: Axonarium & co"],
};

describe("networkSvg", () => {
  const svg = networkSvg([node("a", -50, 0, true), node("b", 50, 20), node("c", 0, -40)], [link("a", "b"), link("a", "c", true), link("a", "gone")], TEXT);

  it("draws every node and each link whose ends are present, with its arrow", () => {
    expect(svg.match(/<circle /g)).toHaveLength(3 + 1); // the nodes, and the legend's swatch
    expect(svg.match(/<path /g)).toHaveLength(2);
    expect(svg.match(/<polygon /g)).toHaveLength(2);
    expect(svg.match(/stroke-dasharray/g)).toHaveLength(1);
  });

  it("frames the plot with the title, legend and caption, escaping text", () => {
    expect(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"')).toBe(true);
    expect(svg).toContain(`fill="${PLOT_BACKGROUND}"`);
    expect(svg).toContain("<title>Where the mouse amygdala projects</title>");
    expect(svg).toContain("A&lt;B");
    expect(svg).toContain("Figure: Axonarium &amp; co");
    expect(svg).not.toContain("A<B");
  });

  it("fits the nodes inside the plot", () => {
    const xs = [...svg.matchAll(/<circle cx="([\d.]+)" cy="([\d.]+)" r="[\d.]+" fill="#(?:f97316|cbd5e1)"\/>/g)].map((m) => Number(m[1]));
    expect(Math.min(...xs)).toBeGreaterThanOrEqual(32);
    expect(Math.max(...xs)).toBeLessThanOrEqual(1200 - 32);
  });

  it("copes with no nodes", () => {
    expect(networkSvg([], [], TEXT)).toContain("</svg>");
  });

  it("wraps a caption too long for the figure's width", () => {
    const narrow = networkSvg([], [], { ...TEXT, caption: ["word ".repeat(100).trim()] }, 400);
    const lines = [...narrow.matchAll(/font-size="12" fill="#475569">([^<]*)</g)].map((m) => m[1]);
    expect(lines.length).toBeGreaterThan(5);
    expect(lines.join(" ")).toBe("word ".repeat(100).trim());
    for (const line of lines) expect(line.length).toBeLessThanOrEqual(Math.floor((400 - 64) / 6.5));
  });
});

describe("wrap", () => {
  it("breaks at spaces within the width, giving a longer word a line to itself", () => {
    expect(wrap("aa bb cc dd", 5)).toEqual(["aa bb", "cc dd"]);
    expect(wrap("a verylongword b", 4)).toEqual(["a", "verylongword", "b"]);
    expect(wrap("", 10)).toEqual([""]);
  });
});
