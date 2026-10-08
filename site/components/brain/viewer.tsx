"use client";

// The 3D brain: BrainGlobe region meshes (glTF from the build), with an arc per connection from the injected
// amygdala region to each target. Loaded only in the browser (components/brain/brain-view.tsx).

import { Html, OrbitControls, QuadraticBezierLine, useGLTF } from "@react-three/drei";
import { Canvas, type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Fragment, type ReactNode, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { download, type FigureText, framedPng, networkSvg, svgPng } from "@/lib/figure";
import { edgeHref, regionHref } from "@/lib/format";
import { reachable, shortestRoute } from "@/lib/route";
import {
  arcMidpoint,
  arcWidth,
  type BrainEdge,
  type BrainGap,
  type BrainIndex,
  type BrainRegion,
  byDensity,
  type Direction,
  directed,
  gapEdge,
  hubOf,
  linkedView,
} from "@/lib/brain";

import type { NetworkFigure } from "./network";
import { ROUTE_COLOR, RoutePanel } from "./route-panel";
import { CANVAS } from "./sizes";

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

/** Renders its children (labels) once the canvas's events are connected. An <Html> mounted before then moves to
 * the connected element afterwards and makes a second React root on the same node, which fails to unmount. */
function WhenConnected({ children }: { children: ReactNode }) {
  const connected = useThree((state) => state.events.connected);
  return connected ? children : null;
}

/** A route's stop, named on the brain. */
function Stop({ region }: { region: BrainRegion }) {
  return (
    <Html position={region.centroid} center distanceFactor={14} zIndexRange={[19, 0]} style={{ pointerEvents: "none" }}>
      <div className="rounded bg-black/75 px-1.5 py-0.5 text-[11px] font-semibold text-yellow-200">{region.acronym}</div>
    </Html>
  );
}

const densityText = (edge: BrainEdge) => (edge.density === null ? "no density stated" : `projection density ${edge.density.toFixed(3)}`);

/** Registers a capture of the 3D view: one frame rendered at twice the resolution and copied out, so the canvas
 * needn't keep its drawing buffer between frames. */
function Snapshot({ register }: { register: (capture: (() => HTMLCanvasElement) | null) => void }) {
  const { gl, scene, camera, size } = useThree();
  useEffect(() => {
    register(() => {
      const ratio = gl.getPixelRatio();
      gl.setPixelRatio(2);
      gl.setSize(size.width, size.height, false);
      gl.render(scene, camera);
      const copy = Object.assign(document.createElement("canvas"), { width: gl.domElement.width, height: gl.domElement.height });
      copy.getContext("2d")?.drawImage(gl.domElement, 0, 0);
      gl.setPixelRatio(ratio);
      gl.setSize(size.width, size.height, false);
      return copy;
    });
    return () => register(null);
  }, [gl, scene, camera, size, register]);
  return null;
}

/** Which connection suggests a gap: a link to the first neighbour's connection to the same target. */
function Suggested({ gap, regions }: { gap?: BrainGap; regions: Record<string, BrainRegion> }) {
  if (!gap || gap.by.length === 0) return null;
  const species = gap.id.split("|").at(-1);
  const names = gap.by.map((id) => regions[id]?.acronym ?? id);
  return (
    <Link
      href={edgeHref(`${gap.by[0]}|projects_to|${gap.target}|${species}`)}
      className="shrink-0 text-xs underline underline-offset-4"
      title={`Suggested by ${names.join(", ")}`}
    >
      via {names[0]}
      {names.length > 1 ? ` +${names.length - 1}` : ""}
    </Link>
  );
}

/** The full viewer, or with `compact` a rotating preview without controls (the home page) that links to it. */
export default function BrainViewer({ edges, gaps = [], base, compact = false }: {
  edges: BrainEdge[];
  /** Gap mode's untested connections (ADR 0027). */
  gaps?: BrainGap[];
  base: string;
  compact?: boolean;
}) {
  const [index, setIndex] = useState<BrainIndex | "missing" | null>(null);
  const [source, setSource] = useState<string>(ALL);
  const [threshold, setThreshold] = useState(0.05);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [view, setView] = useState<"3d" | "network">("3d");
  const [direction, setDirection] = useState<Direction>("outputs");
  // Gap mode (ADR 0027): untested outputs instead of connections; always outputs.
  const [gapMode, setGapMode] = useState(false);

  // The path finder: a route's ends, and how many of its hops are drawn so far.
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [revealed, setRevealed] = useState(0);

  // /brain?region=<id> (from a region's page) opens on that region, and ?from=<id>&to=<id> on a route. The viewer
  // only runs in the browser.
  const [linked] = useState(() => new URLSearchParams(window.location.search).get("region"));
  const [linkedRoute] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return { from: params.get("from") ?? "", to: params.get("to") ?? "" };
  });

  useEffect(() => {
    fetch(`${base}/index.json`)
      // An unread body keeps the request open, so a missing index's body is cancelled.
      .then((response) => (response.ok ? response.json() : response.body?.cancel().then(() => "missing" as const) ?? "missing"))
      .then(
        (found: BrainIndex | "missing") => {
          setIndex(found);
          if (found !== "missing" && found.regions[linkedRoute.from]) {
            setFrom(linkedRoute.from);
            if (found.regions[linkedRoute.to]) setTo(linkedRoute.to);
          }
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
  }, [base, edges, linked, linkedRoute]);

  const regions = useMemo<Record<string, BrainRegion>>(() => (index && index !== "missing" ? index.regions : {}), [index]);
  // `sources` are the amygdala regions at the amygdala end of the chosen direction's connections, or in gap mode
  // the untested regions with gaps.
  const drawable = useMemo(() => directed(edges, regions, direction), [edges, regions, direction]);
  const gapEdges = useMemo(() => gaps.filter((g) => regions[g.source] && regions[g.target]).map(gapEdge), [gaps, regions]);
  const gapsById = useMemo(() => new Map(gaps.map((g) => [g.id, g])), [gaps]);
  const pool = gapMode ? gapEdges : drawable;
  const sources = useMemo(() => {
    const counts = new Map<string, number>();
    for (const edge of pool) counts.set(hubOf(edge, direction), (counts.get(hubOf(edge, direction)) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([id]) => id);
  }, [pool, direction]);
  // One colour per amygdala region, the same in both directions.
  const colors = useMemo(() => {
    const ids = Object.keys(regions).filter((id) => regions[id].amygdala).sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
    return Object.fromEntries(ids.map((id, i) => [id, PALETTE[i % PALETTE.length]]));
  }, [regions]);
  const shown = useMemo(
    () => byDensity(pool.filter((e) => source === ALL || hubOf(e, direction) === source), threshold),
    [pool, direction, source, threshold],
  );
  const other = (e: BrainEdge) => (direction === "outputs" ? e.target : e.source);
  // Stable between renders, so the network keeps its layout while the pointer moves.
  const hub = useCallback((e: BrainEdge) => hubOf(e, direction), [direction]);
  const strongest = shown.reduce((max, e) => Math.max(max, e.density ?? 0), 0);
  const targets = [...new Set(shown.map(other))].filter((id) => !sources.includes(id) || source !== ALL);
  const focus = selected ?? hovered;
  const Turn = compact ? Spin : Fragment;
  const focusEdges = focus ? shown.filter((e) => e.target === focus || e.source === focus) : [];

  // The path finder (lib/route.ts) runs over every drawable connection, whichever the direction.
  const linkable = useMemo(() => edges.filter((e) => regions[e.source] && regions[e.target] && e.source !== e.target), [edges, regions]);
  const byAcronym = useCallback(
    (ids: Iterable<string>) => [...ids].sort((a, b) => regions[a].acronym.localeCompare(regions[b].acronym, "en", { numeric: true })),
    [regions],
  );
  const starts = useMemo(() => byAcronym(new Set(linkable.map((e) => e.source))), [linkable, byAcronym]);
  const ends = useMemo(() => (from ? byAcronym(reachable(linkable, from)) : []), [linkable, from, byAcronym]);
  const hops = useMemo(() => (from && to ? shortestRoute(linkable, from, to) : null), [linkable, from, to]);
  const routing = hops !== null;
  const routeShown = useMemo(() => (hops ? hops.slice(0, revealed) : []), [hops, revealed]);
  const stops = useMemo(() => (hops ? [from, ...routeShown.map((e) => e.target)] : []), [hops, from, routeShown]);
  const routeColors = useMemo(() => Object.fromEntries(stops.map((id) => [id, ROUTE_COLOR])), [stops]);
  const routeHub = useCallback((e: BrainEdge) => e.source, []);
  const drawn = routing ? routeShown : shown;
  // One hop at a time, or all at once for those who ask for less motion.
  useEffect(() => {
    if (!hops || revealed >= hops.length) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = setTimeout(() => setRevealed((n) => n + 1), still ? 0 : revealed === 0 ? 300 : 1100);
    return () => clearTimeout(timer);
  }, [hops, revealed]);
  // The route lives in the URL, so it can be shared.
  useEffect(() => {
    if (compact || !index) return;
    const url = new URL(window.location.href);
    for (const [name, value] of [["from", from], ["to", to]]) {
      if (value) url.searchParams.set(name, value);
      else url.searchParams.delete(name);
    }
    if (url.href !== window.location.href) window.history.replaceState(window.history.state, "", url);
  }, [compact, index, from, to]);
  const chooseFrom = (id: string) => {
    setFrom(id);
    setRevealed(0);
    if (!id || (to && !reachable(linkable, id).has(to))) setTo("");
  };

  // Figure export (lib/figure.ts): the current view as a PNG, the network view as an SVG too.
  const capture3d = useRef<(() => HTMLCanvasElement) | null>(null);
  const networkFigure = useRef<NetworkFigure | null>(null);
  // Each view can be exported once it has registered; until then its buttons are disabled.
  const [exportable, setExportable] = useState({ "3d": false, network: false });
  const register3d = useCallback((capture: (() => HTMLCanvasElement) | null) => {
    capture3d.current = capture;
    setExportable((now) => ({ ...now, "3d": capture !== null }));
  }, []);
  const registerNetwork = useCallback((figure: NetworkFigure | null) => {
    networkFigure.current = figure;
    setExportable((now) => ({ ...now, network: figure !== null }));
  }, []);
  const figureText = (): FigureText => {
    const date = new Date().toISOString().slice(0, 10);
    const papers = (hops ?? (gapMode ? [] : shown)).reduce((n, edge) => n + edge.papers, 0);
    const fromPapers = papers ? `; ${papers} claim${papers === 1 ? "" : "s"} drafted from published papers, each cited at https://axonarium.com` : "";
    const caption = [
      `Data: Allen Mouse Brain Connectivity Atlas (Oh et al. 2014, doi:10.1038/nature13186), © Allen Institute${fromPapers}; region names and meshes: Allen Institute atlases, via BrainGlobe.`,
      `Figure: Axonarium, https://axonarium.com/brain, ${date}. Width: the strongest projection density; dashed: only proposed claims.`,
    ];
    if (hops) {
      const weakest = Math.min(...hops.map((h) => h.density ?? 0));
      return {
        title: `A route from ${regions[from].acronym} to ${regions[to].acronym} in the mouse brain`,
        subtitle: `${hops.length} hop${hops.length === 1 ? "" : "s"}, the fewest there are; weakest hop: projection density ${weakest.toFixed(3)}`,
        legend: [{ label: "Route", color: ROUTE_COLOR }],
        caption: [...caption, `Route: ${[from, ...hops.map((h) => h.target)].map((id) => regions[id].acronym).join(" → ")}.`],
      };
    }
    if (gapMode) {
      return {
        title: "Untested outputs of the mouse amygdala, suggested by neighbouring regions",
        subtitle: `${source === ALL ? "Every amygdala region without reported outputs" : `${regions[source]?.acronym} (${regions[source]?.name})`}; neighbours' projection density ≥ ${threshold}; ${shown.length} suggestion${shown.length === 1 ? "" : "s"}`,
        legend: (source === ALL ? sources : [source]).map((id) => ({ label: regions[id]?.acronym ?? id, color: colors[id] })),
        caption: [
          ...caption.slice(0, 1),
          `Figure: Axonarium, https://axonarium.com/brain, ${date}. Gap mode: regions no claim reports outputs for, to the targets their neighbours project to. Suggestions for experiments, not evidence.`,
        ],
      };
    }
    return {
      title: direction === "outputs" ? "Where the mouse amygdala projects" : "What projects to the mouse amygdala",
      subtitle: `${source === ALL ? "Every amygdala region" : `${regions[source]?.acronym} (${regions[source]?.name})`}; projection density ≥ ${threshold}; ${shown.length} connection${shown.length === 1 ? "" : "s"}`,
      legend: (source === ALL ? sources : [source]).map((id) => ({ label: regions[id]?.acronym ?? id, color: colors[id] })),
      caption,
    };
  };
  const figureSubject = hops
    ? `route-${regions[from].acronym}-${regions[to].acronym}`
    : `${gapMode ? "gaps" : direction}-${source === ALL ? "all" : (regions[source]?.acronym ?? "region")}`;
  const figureName = (extension: string) =>
    `axonarium-${figureSubject.replace(/[^A-Za-z0-9-]+/g, "_")}-${new Date().toISOString().slice(0, 10)}.${extension}`;
  // The network view's figure is drawn from its layout, so the PNG is the SVG at twice the size, every label shown.
  const networkFigureSvg = () => {
    const figure = networkFigure.current;
    return figure ? networkSvg(figure.nodes(), figure.links(), figureText()) : null;
  };
  const exportPng = async () => {
    const svg = view === "network" ? networkFigureSvg() : null;
    const canvas = view === "3d" ? capture3d.current?.() : null;
    if (svg) download(await svgPng(svg), figureName("png"));
    else if (canvas) download(await framedPng(canvas, figureText()), figureName("png"));
  };
  const exportSvg = () => {
    const svg = networkFigureSvg();
    if (svg) download(new Blob([svg], { type: "image/svg+xml" }), figureName("svg"));
  };
  // Clicking an injected region shows only its connections; clicking a target selects it.
  const choose = (id: string | null) => {
    if (id && sources.includes(id) && id !== source) return (setSource(id), setSelected(null));
    setSelected(id === selected ? null : id);
  };

  const canvasBox = compact ? CANVAS.compact : CANVAS.full; // the loading placeholder's size (brain-view.tsx)

  if (index === "missing") {
    return (
      <div className={`grid place-items-center rounded-xl border border-dashed p-6 ${canvasBox}`}>
        <p role="status" className="max-w-md text-sm text-muted-foreground">
          This build has no brain meshes. They&apos;re made by the deploy build (<code>python -m build --meshes</code>);
          the connections are on the{" "}
          <Link href="/explore" className="underline underline-offset-4">
            Explore
          </Link>{" "}
          page.
        </p>
      </div>
    );
  }

  return (
    <div className={compact ? "" : "grid gap-4 lg:grid-cols-[1fr_19rem]"}>
      <div className={`relative overflow-hidden rounded-xl border bg-[#0b1020] ${canvasBox}`}>
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
            shown={drawn}
            regions={regions}
            injected={routing ? stops : sources}
            hub={routing ? routeHub : hub}
            colors={routing ? routeColors : colors}
            strongest={strongest}
            focus={focus}
            onSelect={choose}
            onHover={setHovered}
            register={registerNetwork}
          />
        )}
        {index && view === "3d" && (
          <Canvas
            camera={{ position: CAMERA, fov: 35, near: 0.1, far: 200 }}
            dpr={[1, 2]}
            role="img"
            aria-label="3D view of the mouse brain with the amygdala's projections"
            onPointerMissed={() => setSelected(null)}
            fallback={<p className="p-4 text-sm text-white/70">This browser can&apos;t show 3D. The table on Explore has every connection.</p>}
          >
            <color attach="background" args={["#0b1020"]} />
            {!compact && <Snapshot register={register3d} />}
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
                  opacity={routing ? (stops.includes(id) ? 0.95 : 0.15) : source === ALL || source === id ? 0.95 : 0.25}
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
            {drawn.map((edge, i) => {
              const start = regions[edge.source].centroid;
              const end = regions[edge.target].centroid;
              const dim = focus !== null && edge.target !== focus && edge.source !== focus;
              const latest = routing && i === drawn.length - 1;
              return (
                <QuadraticBezierLine
                  key={edge.id}
                  start={start}
                  end={end}
                  mid={arcMidpoint(start, end)}
                  color={routing ? ROUTE_COLOR : colors[hubOf(edge, direction)]}
                  lineWidth={routing ? (latest ? 4.5 : 3) : arcWidth(edge.density, strongest)}
                  dashed={edge.accepted === 0}
                  dashSize={0.25}
                  gapSize={0.15}
                  transparent
                  opacity={dim ? 0.08 : routing && !latest ? 0.7 : 0.85}
                />
              );
            })}
            {(routing ? stops : targets).map((id) => (
              <mesh
                key={id}
                position={regions[id].centroid}
                onClick={(event) => (event.stopPropagation(), setSelected(selected === id ? null : id))}
                onPointerOver={(event) => (event.stopPropagation(), setHovered(id))}
                onPointerOut={() => setHovered(null)}
              >
                <sphereGeometry args={[focus === id ? 0.16 : 0.1, 16, 16]} />
                <meshBasicMaterial color={routing ? ROUTE_COLOR : source === ALL ? "#e2e8f0" : colors[source]} />
              </mesh>
            ))}
            <WhenConnected>
              {routing && stops.map((id) => <Stop key={id} region={regions[id]} />)}
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
            </WhenConnected>
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
        {!routing && (
          <>
          {gapEdges.length > 0 && (
            <div role="group" aria-label="Show" className="grid grid-cols-2 rounded-lg border p-0.5 text-xs">
              {([false, true] as const).map((on) => (
                <button
                  key={String(on)}
                  type="button"
                  aria-pressed={gapMode === on}
                  onClick={() => (setGapMode(on), setDirection("outputs"), setSource(ALL), setSelected(null))}
                  className="rounded-md px-2 py-1.5 text-muted-foreground transition-colors aria-pressed:bg-foreground aria-pressed:text-background"
                >
                  {on ? "Untested (gap mode)" : "Connections"}
                </button>
              ))}
            </div>
          )}
          {!gapMode && (
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
          )}
          {gapMode && (
            <p className="text-xs text-muted-foreground">
              Amygdala regions that no claim reports outputs for (no tracer injection is known), drawn to the targets their
              neighbours, other parts of the same structure, project to. Width: the strongest neighbour&apos;s density.
              Suggestions for experiments, not evidence.
            </p>
          )}
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
              {gapMode
                ? `${shown.length} untested connection${shown.length === 1 ? "" : "s"}, best suggested first`
                : `${shown.length} connection${shown.length === 1 ? "" : "s"}, strongest first`}
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
                    {gapMode ? (
                      <Suggested gap={gapsById.get(edge.id)} regions={regions} />
                    ) : (
                      <Link href={`/edges/${edge.id}`} className="text-xs underline underline-offset-4" aria-label="Evidence">
                        claims
                      </Link>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
          </>
        )}

        <RoutePanel
          regions={regions}
          starts={starts}
          ends={ends}
          from={from}
          to={to}
          hops={hops}
          revealed={revealed}
          onFrom={chooseFrom}
          onTo={(id) => (setTo(id), setRevealed(0))}
          onReplay={() => setRevealed(0)}
          onClear={() => chooseFrom("")}
        />

        <div className="space-y-2">
          <h2 className="font-medium">Figure</h2>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="outline" onClick={exportPng} disabled={!exportable[view]}>
              Download PNG
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={exportSvg} disabled={view !== "network" || !exportable.network}>
              Download SVG
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            This view with a title, legend and citation, for a paper or a talk. SVG comes from the network view.
          </p>
        </div>

        {!gapMode && (
          <p className="text-xs text-muted-foreground">
            Outputs come from tracer injected into the amygdala; inputs from injections elsewhere that label it.
            Arc width: the strongest projection density among a connection&apos;s claims; connections that state no
            density, as most from papers don&apos;t, are drawn thinnest and listed last, whatever the minimum. Dashed:
            every claim is proposed, because most of an Allen injection landed outside the named region or because
            AI models drafted it from a paper and people haven&apos;t audited it yet. Densities pool both hemispheres;
            3D arcs are drawn on the right, where Allen injects. Drag to turn or move, scroll to zoom, click a region or a row.
          </p>
        )}
      </aside>
    </div>
  );
}
