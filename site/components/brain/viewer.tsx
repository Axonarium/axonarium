"use client";

// The 3D brain: BrainGlobe region meshes (glTF from the build), with an arc per connection from the injected
// amygdala region to each target. Loaded only in the browser (components/brain/brain-view.tsx).

import { Html, OrbitControls, QuadraticBezierLine, useGLTF } from "@react-three/drei";
import { Canvas, type ThreeEvent, useThree } from "@react-three/fiber";
import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import * as THREE from "three";

import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { arcMidpoint, arcWidth, type BrainEdge, type BrainIndex, type BrainRegion } from "@/lib/brain";

const PALETTE = ["#f97316", "#22d3ee", "#a78bfa", "#f43f5e", "#84cc16", "#facc15", "#38bdf8", "#e879f9", "#34d399", "#fb7185"];
const THRESHOLDS = [0.01, 0.05, 0.1, 0.2];
const ALL = "all";
const CAMERA: [number, number, number] = [19, 9, -9];

/** Moves the camera back on narrow screens, so the whole brain stays in view. */
function FitCamera() {
  const { camera, size } = useThree();
  useEffect(() => {
    const scale = Math.max(1, 1.3 / (size.width / size.height));
    camera.position.set(CAMERA[0] * scale, CAMERA[1] * scale, CAMERA[2] * scale);
  }, [camera, size.width, size.height]);
  return null;
}

function useGeometry(url: string): THREE.BufferGeometry | null {
  const { scene } = useGLTF(url);
  return useMemo(() => {
    let found: THREE.BufferGeometry | null = null;
    scene.traverse((object) => {
      if (!found && (object as THREE.Mesh).isMesh) found = (object as THREE.Mesh).geometry;
    });
    return found;
  }, [scene]);
}

function RegionMesh({ url, color, opacity, onClick, onHover }: {
  url: string;
  color: string;
  opacity: number;
  onClick?: () => void;
  onHover?: (over: boolean) => void;
}) {
  const geometry = useGeometry(url);
  if (!geometry) return null;
  const translucent = opacity < 1;
  return (
    <mesh
      geometry={geometry}
      renderOrder={translucent ? 1 : 0}
      onClick={onClick && ((event: ThreeEvent<MouseEvent>) => (event.stopPropagation(), onClick()))}
      onPointerOver={onHover && ((event: ThreeEvent<PointerEvent>) => (event.stopPropagation(), onHover(true)))}
      onPointerOut={onHover && (() => onHover(false))}
    >
      <meshStandardMaterial
        color={color}
        transparent={translucent}
        opacity={opacity}
        depthWrite={!translucent}
        side={translucent ? THREE.DoubleSide : THREE.FrontSide}
        roughness={0.6}
      />
    </mesh>
  );
}

function Label({ region, detail }: { region: BrainRegion; detail?: string }) {
  return (
    <Html position={region.centroid} center distanceFactor={14} zIndexRange={[20, 0]} style={{ pointerEvents: "none" }}>
      <div className="whitespace-nowrap rounded-md bg-black/80 px-2 py-1 text-xs text-white shadow">
        <span className="font-semibold">{region.acronym}</span> {region.name}
        {detail && <span className="block text-white/70">{detail}</span>}
      </div>
    </Html>
  );
}

const densityText = (edge: BrainEdge) => (edge.density === null ? "no density stated" : `projection density ${edge.density.toFixed(3)}`);

export default function BrainViewer({ edges, base }: { edges: BrainEdge[]; base: string }) {
  const [index, setIndex] = useState<BrainIndex | "missing" | null>(null);
  const [source, setSource] = useState<string>(ALL);
  const [threshold, setThreshold] = useState(0.05);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${base}/index.json`)
      .then((response) => (response.ok ? response.json() : "missing"))
      .then(setIndex, () => setIndex("missing"));
  }, [base]);

  const regions = useMemo<Record<string, BrainRegion>>(() => (index && index !== "missing" ? index.regions : {}), [index]);
  const drawable = useMemo(() => edges.filter((e) => regions[e.source] && regions[e.target]), [edges, regions]);
  const sources = useMemo(() => {
    const counts = new Map<string, number>();
    for (const edge of drawable) counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([id]) => id);
  }, [drawable]);
  const colors = useMemo(() => Object.fromEntries(sources.map((id, i) => [id, PALETTE[i % PALETTE.length]])), [sources]);
  const shown = useMemo(
    () =>
      drawable
        .filter((e) => (source === ALL || e.source === source) && (e.density ?? 0) >= threshold)
        .sort((a, b) => (b.density ?? 0) - (a.density ?? 0)),
    [drawable, source, threshold],
  );
  const strongest = shown.reduce((max, e) => Math.max(max, e.density ?? 0), 0);
  const targets = [...new Set(shown.map((e) => e.target))].filter((id) => !sources.includes(id) || source !== ALL);
  const focus = selected ?? hovered;
  const focusEdges = focus ? shown.filter((e) => e.target === focus || e.source === focus) : [];

  if (index === "missing") {
    return (
      <p role="status" className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
        This build has no brain meshes. They&apos;re made by the deploy build (<code>python -m build --meshes</code>);
        the connections are on the{" "}
        <Link href="/explore" className="underline underline-offset-4">
          Explore
        </Link>{" "}
        page.
      </p>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_19rem]">
      <div className="relative h-[min(60vh,110vw)] min-h-[320px] overflow-hidden rounded-xl border bg-[#0b1020] lg:h-[62vh]">
        {index === null && <p className="absolute inset-0 grid place-items-center text-sm text-white/60">Loading the atlas…</p>}
        {index && (
          <Canvas
            camera={{ position: CAMERA, fov: 35, near: 0.1, far: 200 }}
            dpr={[1, 2]}
            aria-label="3D view of the mouse brain with the amygdala's projections"
            onPointerMissed={() => setSelected(null)}
            fallback={<p className="p-4 text-sm text-white/70">This browser can&apos;t show 3D. The table on Explore has every connection.</p>}
          >
            <color attach="background" args={["#0b1020"]} />
            <FitCamera />
            <ambientLight intensity={0.7} />
            <directionalLight position={[10, 15, -5]} intensity={1.6} />
            <directionalLight position={[-10, -5, 10]} intensity={0.5} />
            <Suspense fallback={null}>
              <RegionMesh url={`${base}/${index.root}`} color="#9fb3d1" opacity={0.08} />
            </Suspense>
            {sources.map((id) => (
              <Suspense key={id} fallback={null}>
                <RegionMesh
                  url={`${base}/${regions[id].file}`}
                  color={colors[id]}
                  opacity={source === ALL || source === id ? 0.95 : 0.25}
                  onClick={() => setSource(source === id ? ALL : id)}
                  onHover={(over) => setHovered(over ? id : null)}
                />
              </Suspense>
            ))}
            {selected && !sources.includes(selected) && regions[selected] && (
              <Suspense fallback={null}>
                <RegionMesh url={`${base}/${regions[selected].file}`} color="#e2e8f0" opacity={0.35} />
              </Suspense>
            )}
            {shown.map((edge) => {
              const start = regions[edge.source].centroid;
              const end = regions[edge.target].centroid;
              const dim = focus !== null && edge.target !== focus && edge.source !== focus;
              return (
                <QuadraticBezierLine
                  key={edge.id}
                  start={start}
                  end={end}
                  mid={arcMidpoint(start, end)}
                  color={colors[edge.source]}
                  lineWidth={arcWidth(edge.density, strongest)}
                  dashed={edge.accepted === 0}
                  dashSize={0.25}
                  gapSize={0.15}
                  transparent
                  opacity={dim ? 0.08 : 0.85}
                />
              );
            })}
            {targets.map((id) => (
              <mesh
                key={id}
                position={regions[id].centroid}
                onClick={(event) => (event.stopPropagation(), setSelected(selected === id ? null : id))}
                onPointerOver={(event) => (event.stopPropagation(), setHovered(id))}
                onPointerOut={() => setHovered(null)}
              >
                <sphereGeometry args={[focus === id ? 0.16 : 0.1, 16, 16]} />
                <meshBasicMaterial color={source === ALL ? "#e2e8f0" : colors[source]} />
              </mesh>
            ))}
            {focus && regions[focus] && (
              <Label
                region={regions[focus]}
                detail={
                  focusEdges.length === 1
                    ? `${regions[focusEdges[0].source].acronym} → ${regions[focusEdges[0].target].acronym}: ${densityText(focusEdges[0])}`
                    : `${focusEdges.length} connections shown`
                }
              />
            )}
            <OrbitControls makeDefault enableDamping autoRotate={focus === null} autoRotateSpeed={0.4} minDistance={6} maxDistance={60} />
          </Canvas>
        )}
      </div>

      <aside className="space-y-4 text-sm">
        <div className="space-y-2">
          <h2 className="font-medium">Injected region</h2>
          <div className="flex flex-wrap gap-1.5">
            {[ALL, ...sources].map((id) => (
              <button
                key={id}
                type="button"
                aria-pressed={source === id}
                onClick={() => (setSource(id), setSelected(null))}
                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors hover:bg-muted aria-pressed:border-foreground aria-pressed:bg-muted"
                title={id === ALL ? "Every amygdala injection" : regions[id]?.name}
              >
                {id !== ALL && <span className="size-2.5 rounded-full" style={{ background: colors[id] }} />}
                {id === ALL ? "All" : regions[id]?.acronym}
              </button>
            ))}
          </div>
          {source !== ALL && regions[source] && <p className="text-muted-foreground">{regions[source].name}</p>}
        </div>

        <label className="flex items-center justify-between gap-3">
          <span className="font-medium">Minimum density</span>
          <NativeSelect size="sm" value={threshold} onChange={(event) => setThreshold(Number(event.target.value))}>
            {THRESHOLDS.map((t) => (
              <NativeSelectOption key={t} value={t}>
                {t}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </label>

        <div className="space-y-2">
          <h2 className="font-medium">
            {shown.length} connection{shown.length === 1 ? "" : "s"}, strongest first
          </h2>
          <ol className="max-h-[38vh] space-y-1 overflow-y-auto pr-1">
            {shown.slice(0, 40).map((edge) => (
              <li key={edge.id}>
                <div
                  className={`flex items-center gap-2 rounded-md px-2 py-1 ${selected === edge.target ? "bg-muted" : "hover:bg-muted/60"}`}
                >
                  <span className="size-2 shrink-0 rounded-full" style={{ background: colors[edge.source] }} />
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate text-left"
                    title={`${regions[edge.source].name} → ${regions[edge.target].name}`}
                    onClick={() => setSelected(selected === edge.target ? null : edge.target)}
                  >
                    {regions[edge.source].acronym} → <span className="font-medium">{regions[edge.target].acronym}</span>
                  </button>
                  <span className="tabular-nums text-muted-foreground">{edge.density?.toFixed(3) ?? "–"}</span>
                  <Link href={`/edges/${edge.id}`} className="text-xs underline underline-offset-4" aria-label="Evidence">
                    claims
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <p className="text-xs text-muted-foreground">
          Arc width: the strongest projection density among a connection&apos;s claims. Dashed: every claim is
          proposed, because most of the tracer landed outside the named region. Densities pool both hemispheres;
          arcs are drawn on the right, where Allen injects. Drag to rotate, scroll to zoom, click a dot or a row.
        </p>
      </aside>
    </div>
  );
}
