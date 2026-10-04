"use client";

// The network view of the same connections as the 3D brain (react-force-graph, plan: Network view). Shares the
// viewer's selection, so choosing a region in either view highlights it in both.

import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, { type ForceGraphMethods, type LinkObject, type NodeObject } from "react-force-graph-2d";

import { arcWidth, type BrainEdge, type BrainRegion, type NetworkLink, type NetworkNode, networkData } from "@/lib/brain";

type Node = NodeObject<NetworkNode>;
type Link = LinkObject<NetworkNode, NetworkLink>;

const TARGET = "#cbd5e1";

// After the first layout tick the library has swapped link ends for node objects.
const endId = (end: unknown) => String(end && typeof end === "object" ? (end as { id?: unknown }).id : end);

export default function Network({ shown, regions, injected, colors, strongest, focus, onSelect, onHover }: {
  shown: BrainEdge[];
  regions: Record<string, BrainRegion>;
  injected: string[];
  colors: Record<string, string>;
  strongest: number;
  focus: string | null;
  onSelect: (id: string | null) => void;
  onHover: (id: string | null) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const graph = useRef<ForceGraphMethods<Node, Link> | undefined>(undefined);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const data = useMemo(() => networkData(shown, regions, injected), [shown, regions, injected]);
  const neighbours = useMemo(() => {
    if (!focus) return null;
    const found = new Set([focus]);
    for (const e of shown) if (e.source === focus || e.target === focus) found.add(e.source).add(e.target);
    return found;
  }, [focus, shown]);

  useEffect(() => {
    const element = box.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height }),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    graph.current?.d3Force("charge")?.strength(-140);
    graph.current?.d3Force("link")?.distance(45);
  }, [data]);

  const radius = (node: Node) => (node.injected ? 7 : 2.5 + Math.sqrt(node.inputs) * 1.6);
  const lit = (id: string) => !neighbours || neighbours.has(id);

  return (
    <div ref={box} className="absolute inset-0">
      {size.width > 0 && (
        <ForceGraph2D<NetworkNode, NetworkLink>
          ref={graph}
          width={size.width}
          height={size.height}
          graphData={data}
          backgroundColor="#0b1020"
          cooldownTicks={200}
          onEngineStop={() => graph.current?.zoomToFit(400, 30)}
          nodeLabel={(node) => `${node.acronym}: ${node.name}`}
          nodeCanvasObject={(node, ctx, scale) => {
            const r = radius(node);
            ctx.globalAlpha = lit(String(node.id)) ? 1 : 0.15;
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, r, 0, 2 * Math.PI);
            ctx.fillStyle = node.injected ? colors[String(node.id)] : TARGET;
            ctx.fill();
            if (node.id === focus) {
              ctx.lineWidth = 2 / scale;
              ctx.strokeStyle = "#ffffff";
              ctx.stroke();
            }
            if (node.injected || scale > 1.6 || (neighbours?.has(String(node.id)) ?? false)) {
              ctx.font = `${(node.injected ? 13 : 11) / scale}px sans-serif`;
              ctx.textAlign = "center";
              ctx.textBaseline = "top";
              ctx.fillStyle = "#f8fafc";
              ctx.fillText(node.acronym, node.x ?? 0, (node.y ?? 0) + r + 2 / scale);
            }
            ctx.globalAlpha = 1;
          }}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, radius(node) + 2, 0, 2 * Math.PI);
            ctx.fill();
          }}
          linkColor={(link) => {
            const on = !neighbours || (endId(link.source) === focus || endId(link.target) === focus);
            return `${colors[link.from]}${on ? "cc" : "14"}`;
          }}
          linkWidth={(link) => arcWidth(link.density, strongest) * 0.6}
          linkLineDash={(link) => (link.accepted === 0 ? [3, 2] : null)}
          linkCurvature={0.12}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={0.92}
          linkDirectionalParticles={(link) => (focus && (endId(link.source) === focus || endId(link.target) === focus) ? 2 : 0)}
          linkDirectionalParticleWidth={2.5}
          onNodeClick={(node) => onSelect(String(node.id))}
          onNodeHover={(node) => onHover(node ? String(node.id) : null)}
          onBackgroundClick={() => onSelect(null)}
        />
      )}
    </div>
  );
}
