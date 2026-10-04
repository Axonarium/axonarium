"use client";

import dynamic from "next/dynamic";

import type { BrainEdge } from "@/lib/brain";

import { CANVAS } from "./sizes";

const placeholder = (size: string) =>
  function Placeholder() {
    return <div className={`${size} animate-pulse rounded-xl border bg-[#0b1020]`} />;
  };

// three.js needs the browser's WebGL, so the viewer is never prerendered. Each size has its own placeholder.
const FullViewer = dynamic(() => import("./viewer"), { ssr: false, loading: placeholder(CANVAS.full) });
const CompactViewer = dynamic(() => import("./viewer"), { ssr: false, loading: placeholder(CANVAS.compact) });

export function BrainView({ edges, base, compact = false }: { edges: BrainEdge[]; base: string; compact?: boolean }) {
  return compact ? <CompactViewer edges={edges} base={base} compact /> : <FullViewer edges={edges} base={base} />;
}
