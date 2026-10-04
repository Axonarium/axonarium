"use client";

// The 3D brain: BrainGlobe region meshes (glTF from the build), with an arc per connection from the injected
// amygdala region to each target. Loaded only in the browser (components/brain/brain-view.tsx).

import { Html, OrbitControls, QuadraticBezierLine, useGLTF } from "@react-three/drei";
import { Canvas, type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Fragment, type ReactNode, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { regionHref } from "@/lib/format";
import {
  arcMidpoint,
  arcWidth,
  type BrainEdge,
  type BrainIndex,
  type BrainRegion,
  byDensity,
  type Direction,
  directed,
  hubOf,
  linkedView,
} from "@/lib/brain";

const PALETTE = [
  "#f97316", "#22d3ee", "#a78bfa", "#f43f5e", "#84cc16", "#facc15", "#38bdf8", "#e879f9", "#34d399", "#fb7185", "#a3e635", "#fbbf24",
];
const THRESHOLDS = [0.01, 0.05, 0.1, 0.2];
const ALL = "all";
// The network view loads only when chosen.
const Network = dynamic(() => import("./network"), { ssr: false });
const CAMERA: [number, number, number] = [19, 9, -9];

/** Moves the camera back on narrow screens, so the whole brain stays in view. */
function FitCamera() {
  const { camera, size } = useThree();
  useEffect(() => {
    const scale = Math.max(1, 1.3 / (size.width / size.height));
    camera.position.set(CAMERA[0] * scale, CAMERA[1] * scale, CAMERA[2] * scale);
    camera.lookAt(0, 0, 0);
  }, [camera, size.width, size.height]);
  return null;
}

/** Turns its contents slowly: the compact view's motion, without orbit controls, which would take over touch
 * scrolling on phones. */
function Spin({ children }: { children: ReactNode }) {
  const group = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (group.current) group.current.rotation.y += delta * 0.15;
  });
  return <group ref={group}>{children}</group>;
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

/** The full viewer, or with `compact` a rotating preview without controls (the home page) that links to it. */
export default function BrainViewer({ edges, base, compact = false }: { edges: BrainEdge[]; base: string; compact?: boolean }) {
  const [index, setIndex] = useState<BrainIndex | "missing" | null>(null);
  const [source, setSource] = useState<string>(ALL);
  const [threshold, setThreshold] = useState(0.05);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [view, setView] = useState<"3d" | "network">("3d");
  const [direction, setDirection] = useState<Direction>("outputs");

  // /brain?region=<id> (from a region's page) opens on that region. The viewer only runs in the browser.
  const [linked] = useState(() => new URLSearchParams(window.location.search).get("region"));

  useEffect(() => {
    fetch(`${base}/index.json`)
      .then((response) => (response.ok ? response.json() : "missing"))
      .then(
        (found: BrainIndex | "missing") => {
          setIndex(found);
          if (!linked || found === "missing") return;
          const view = linkedView(edges, found.regions, linked);
          if (!view) return;
          setDirection(view.direction);
          if (view.source) setSource(view.source);
          if (view.selected) setSelected(view.selected);
          setThreshold(0.01); // so all of the region's connections show
        },
        () => setIndex("missing"),
      );
  }, [base, edges, linked]);

  const regions = useMemo<Record<string, BrainRegion>>(() => (index && index !== "missing" ? index.regions : {}), [index]);
  // `sources` are the amygdala regions at the amygdala end of the chosen direction's connections.
  const drawable = useMemo(() => directed(edges, regions, direction), [edges, regions, direction]);
  const sources = useMemo(() => {
    const counts = new Map<string, number>();
    for (const edge of drawable) counts.set(hubOf(edge, direction), (counts.get(hubOf(edge, direction)) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([id]) => id);
  }, [drawable, direction]);
  // One colour per amygdala region, the same in both directions.
  const colors = useMemo(() => {
    const ids = Object.keys(regions).filter((id) => regions[id].amygdala).sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
    return Object.fromEntries(ids.map((id, i) => [id, PALETTE[i % PALETTE.length]]));
  }, [regions]);
  const shown = useMemo(
    () => byDensity(drawable.filter((e) => source === ALL || hubOf(e, direction) === source), threshold),
    [drawable, direction, source, threshold],
  );
  const other = (e: BrainEdge) => (direction === "outputs" ? e.target : e.source);
  // Stable between renders, so the network keeps its layout while the pointer moves.
  const hub = useCallback((e: BrainEdge) => hubOf(e, direction), [direction]);
  const strongest = shown.reduce((max, e) => Math.max(max, e.density ?? 0), 0);
  const targets = [...new Set(shown.map(other))].filter((id) => !sources.includes(id) || source !== ALL);
  const focus = selected ?? hovered;
  const Turn = compact ? Spin : Fragment;
  const focusEdges = focus ? shown.filter((e) => e.target === focus || e.source === focus) : [];
  // Clicking an injected region shows only its connections; clicking a target selects it.
  const choose = (id: string | null) => {
    if (id && sources.includes(id) && id !== source) return (setSource(id), setSelected(null));
    setSelected(id === selected ? null : id);
  };

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
    <div className={compact ? "" : "grid gap-4 lg:grid-cols-[1fr_19rem]"}>
      <div
        className={`relative overflow-hidden rounded-xl border bg-[#0b1020] ${compact ? "h-[min(52vh,95vw)] min-h-[300px]" : "h-[min(60vh,110vw)] min-h-[320px] lg:h-[62vh]"}`}
      >
        {index === null && <p className="absolute inset-0 grid place-items-center text-sm text-white/60">Loading the atlas…</p>}
        {compact && index && (
          <Link
            href="/brain"
            className="absolute right-3 bottom-3 z-10 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-900 shadow hover:bg-white/90"
          >
            Explore in 3D →
          </Link>
        )}
        {!compact && index && (
          <div role="group" aria-label="View" className="absolute top-3 left-3 z-10 flex rounded-full bg-white/10 p-0.5 text-xs backdrop-blur">
            {(["3d", "network"] as const).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={view === v}
                onClick={() => setView(v)}
                className="rounded-full px-3 py-1 text-white/70 transition-colors hover:text-white aria-pressed:bg-white aria-pressed:text-slate-900"
              >
                {v === "3d" ? "3D" : "Network"}
              </button>
            ))}
          </div>
        )}
        {index && view === "network" && (
          <Network
            shown={shown}
            regions={regions}
            injected={sources}
            hub={hub}
            colors={colors}
            strongest={strongest}
            focus={focus}
            onSelect={choose}
            onHover={setHovered}
          />
        )}
        {index && view === "3d" && (
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
            <Turn>
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
                  color={colors[hubOf(edge, direction)]}
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
            </Turn>
            {!compact && (
              <OrbitControls
                makeDefault
                enableDamping
                autoRotate={focus === null}
                autoRotateSpeed={0.4}
                minDistance={6}
                maxDistance={60}
              />
            )}
          </Canvas>
        )}
      </div>

      <aside className={compact ? "hidden" : "space-y-4 text-sm"}>
        <div role="group" aria-label="Direction" className="grid grid-cols-2 rounded-lg border p-0.5 text-xs">
          {(["outputs", "inputs"] as const).map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={direction === d}
              onClick={() => (setDirection(d), setSource(ALL), setSelected(null))}
              className="rounded-md px-2 py-1.5 text-muted-foreground transition-colors aria-pressed:bg-foreground aria-pressed:text-background"
            >
              {d === "outputs" ? "Where it projects" : "What projects to it"}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          <h2 className="font-medium">Amygdala region</h2>
          <div className="flex flex-wrap gap-1.5">
            {[ALL, ...sources].map((id) => (
              <button
                key={id}
                type="button"
                aria-pressed={source === id}
                onClick={() => (setSource(id), setSelected(null))}
                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors hover:bg-muted aria-pressed:border-foreground aria-pressed:bg-muted"
                title={id === ALL ? "Every amygdala region" : regions[id]?.name}
              >
                {id !== ALL && <span className="size-2.5 rounded-full" style={{ background: colors[id] }} />}
                {id === ALL ? "All" : regions[id]?.acronym}
              </button>
            ))}
          </div>
          {source !== ALL && regions[source] && (
            <p className="text-muted-foreground">
              <Link href={regionHref(source)} className="underline underline-offset-4">
                {regions[source].name}
              </Link>
            </p>
          )}
        </div>

        {selected && regions[selected] && (
          <p className="rounded-md border px-2.5 py-1.5">
            Selected:{" "}
            <Link href={regionHref(selected)} className="font-medium underline underline-offset-4">
              {regions[selected].acronym}
            </Link>{" "}
            <span className="text-muted-foreground">{regions[selected].name}</span>
          </p>
        )}

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
                  className={`flex items-center gap-2 rounded-md px-2 py-1 ${selected === other(edge) ? "bg-muted" : "hover:bg-muted/60"}`}
                >
                  <span className="size-2 shrink-0 rounded-full" style={{ background: colors[hubOf(edge, direction)] }} />
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate text-left"
                    title={`${regions[edge.source].name} → ${regions[edge.target].name}`}
                    onClick={() => setSelected(selected === other(edge) ? null : other(edge))}
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
          Outputs come from tracer injected into the amygdala; inputs from injections elsewhere that label it.
          Arc width: the strongest projection density among a connection&apos;s claims; connections that state no
          density are drawn thinnest and listed last, whatever the minimum. Dashed: every claim is
          proposed, because most of the tracer landed outside the named region. Densities pool both hemispheres;
          3D arcs are drawn on the right, where Allen injects. Drag to turn or move, scroll to zoom, click a region or a row.
        </p>
      </aside>
    </div>
  );
}
