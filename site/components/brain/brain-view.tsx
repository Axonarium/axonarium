"use client";

import dynamic from "next/dynamic";

import type { BrainEdge } from "@/lib/brain";

// three.js needs the browser's WebGL, so the viewer is never prerendered.
const BrainViewer = dynamic(() => import("./viewer"), {
  ssr: false,
  loading: () => <div className="h-[min(60vh,110vw)] min-h-[320px] animate-pulse rounded-xl border bg-[#0b1020] lg:h-[62vh]" />,
});

export function BrainView({ edges, base, compact = false }: { edges: BrainEdge[]; base: string; compact?: boolean }) {
  return <BrainViewer edges={edges} base={base} compact={compact} />;
}
