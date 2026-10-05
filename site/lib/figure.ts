// Figure export (sprint 3.5): the brain viewer's current view as a PNG, or the network view as an SVG, framed for a
// paper or a talk with a title, a legend and the citation the data's terms ask for. The plot keeps the viewer's dark
// background, the colours it was chosen for; the frame around it is white.

export interface FigureText {
  title: string;
  subtitle: string;
  legend: { label: string; color: string }[];
  caption: string[];
}

export interface FigureNode {
  id: string;
  acronym: string;
  x: number;
  y: number;
  r: number;
  color: string;
  injected: boolean;
}

export interface FigureLink {
  source: string;
  target: string;
  color: string;
  width: number;
  dashed: boolean;
}

export const PLOT_BACKGROUND = "#0b1020";
const INK = "#0f172a";
const MUTED = "#475569";
const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif";
const MARGIN = 32;
const CURVATURE = 0.12; // as the live network view draws its links

const escape = (text: string) =>
  text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[c]!);
const round = (n: number) => Math.round(n * 10) / 10;

const CHAR_WIDTH = 6.5; // a generous average for the caption's 12px sans-serif

/** Words to lines of at most `chars` characters (a longer word gets a line to itself). */
export function wrap(text: string, chars: number): string[] {
  const lines: string[] = [];
  for (const word of text.split(" ")) {
    const last = lines.at(-1);
    if (last !== undefined && last.length + 1 + word.length <= chars) lines[lines.length - 1] = `${last} ${word}`;
    else lines.push(word);
  }
  return lines;
}

/** The frame's parts for a figure `width` wide, shared by the SVG and the PNG: the legend's columns, the caption's
 * wrapped lines, and the heights above and below the plot. */
function layout(text: FigureText, width: number) {
  const perRow = Math.max(1, Math.floor((width - 2 * MARGIN) / 110));
  const legendRows = Math.ceil(text.legend.length / perRow);
  const caption = text.caption.flatMap((line) => wrap(line, Math.floor((width - 2 * MARGIN) / CHAR_WIDTH)));
  const top = MARGIN + 28 + 22 + (legendRows ? 12 + legendRows * 22 : 0) + 16;
  const bottom = 16 + caption.length * 18 + MARGIN;
  return { perRow, caption, top, bottom };
}

function frameSvg(text: FigureText, frame: ReturnType<typeof layout>, plotBottom: number): string {
  const parts = [
    `<text x="${MARGIN}" y="${MARGIN + 22}" font-size="22" font-weight="600" fill="${INK}">${escape(text.title)}</text>`,
    `<text x="${MARGIN}" y="${MARGIN + 46}" font-size="14" fill="${MUTED}">${escape(text.subtitle)}</text>`,
  ];
  text.legend.forEach((item, i) => {
    const x = MARGIN + (i % frame.perRow) * 110;
    const y = MARGIN + 50 + 12 + Math.floor(i / frame.perRow) * 22 + 12;
    parts.push(`<circle cx="${x + 6}" cy="${y}" r="6" fill="${escape(item.color)}"/>`);
    parts.push(`<text x="${x + 18}" y="${y + 5}" font-size="13" fill="${INK}">${escape(item.label)}</text>`);
  });
  frame.caption.forEach((line, i) => {
    parts.push(`<text x="${MARGIN}" y="${plotBottom + 16 + 13 + i * 18}" font-size="12" fill="${MUTED}">${escape(line)}</text>`);
  });
  return parts.join("");
}

/** A point and the direction of travel at `t` along a quadratic Bézier curve. */
function along(p0: number[], p1: number[], p2: number[], t: number) {
  const u = 1 - t;
  const point = [u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]];
  const tangent = [2 * u * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0]), 2 * u * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])];
  return { point, tangent };
}

/** The network view as an SVG: its nodes where the layout left them, fitted to the plot. */
export function networkSvg(nodes: FigureNode[], links: FigureLink[], text: FigureText, width = 1200, plotHeight = 760): string {
  const frame = layout(text, width);
  const height = frame.top + plotHeight + frame.bottom;
  const plot = { x: MARGIN, y: frame.top, w: width - 2 * MARGIN, h: plotHeight };
  const pad = 40;
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const [minX, maxX, minY, maxY] = nodes.length ? [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)] : [0, 1, 0, 1];
  const scale = Math.min((plot.w - 2 * pad) / Math.max(maxX - minX, 1), (plot.h - 2 * pad) / Math.max(maxY - minY, 1), 6);
  const at = (n: FigureNode) => [
    plot.x + plot.w / 2 + (n.x - (minX + maxX) / 2) * scale,
    plot.y + plot.h / 2 + (n.y - (minY + maxY) / 2) * scale,
  ];
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const body: string[] = [];
  for (const link of links) {
    const a = byId.get(link.source);
    const b = byId.get(link.target);
    if (!a || !b) continue;
    const p0 = at(a);
    const p2 = at(b);
    const [dx, dy] = [p2[0] - p0[0], p2[1] - p0[1]];
    const p1 = [(p0[0] + p2[0]) / 2 + dy * CURVATURE, (p0[1] + p2[1]) / 2 - dx * CURVATURE];
    const dash = link.dashed ? ` stroke-dasharray="6 4"` : "";
    body.push(
      `<path d="M${round(p0[0])} ${round(p0[1])}Q${round(p1[0])} ${round(p1[1])} ${round(p2[0])} ${round(p2[1])}" fill="none" stroke="${escape(link.color)}" stroke-opacity="0.8" stroke-width="${round(link.width)}"${dash}/>`,
    );
    const { point, tangent } = along(p0, p1, p2, 0.92);
    const length = Math.hypot(tangent[0], tangent[1]) || 1;
    const [ux, uy] = [tangent[0] / length, tangent[1] / length];
    const size = 7;
    const tip = [point[0] + ux * size * 0.5, point[1] + uy * size * 0.5];
    const back = [point[0] - ux * size * 0.5, point[1] - uy * size * 0.5];
    const corners = [tip, [back[0] - uy * size * 0.45, back[1] + ux * size * 0.45], [back[0] + uy * size * 0.45, back[1] - ux * size * 0.45]];
    body.push(`<polygon points="${corners.map((c) => `${round(c[0])},${round(c[1])}`).join(" ")}" fill="${escape(link.color)}"/>`);
  }
  for (const node of nodes) {
    const [x, y] = at(node);
    const r = node.r * 1.6;
    body.push(`<circle cx="${round(x)}" cy="${round(y)}" r="${round(r)}" fill="${escape(node.color)}"/>`);
    body.push(
      `<text x="${round(x)}" y="${round(y + r + 13)}" font-size="${node.injected ? 14 : 11}" text-anchor="middle" fill="#f8fafc">${escape(node.acronym)}</text>`,
    );
  }
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="${FONT}">`,
    `<title>${escape(text.title)}</title>`,
    `<rect width="${width}" height="${height}" fill="#ffffff"/>`,
    frameSvg(text, frame, plot.y + plot.h),
    `<rect x="${plot.x}" y="${plot.y}" width="${plot.w}" height="${plot.h}" rx="8" fill="${PLOT_BACKGROUND}"/>`,
    ...body,
    "</svg>",
  ].join("\n");
}

const image = async (svg: string) => {
  const found = new Image();
  found.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  await found.decode();
  return found;
};

const png = (canvas: HTMLCanvasElement) =>
  new Promise<Blob>((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("no PNG"))), "image/png"));

/** An SVG figure (networkSvg's) as a PNG at `scale` times its size, for slides. Runs in the browser. */
export async function svgPng(svg: string, scale = 2): Promise<Blob> {
  const drawn = await image(svg);
  const canvas = Object.assign(document.createElement("canvas"), { width: drawn.naturalWidth * scale, height: drawn.naturalHeight * scale });
  canvas.getContext("2d")!.drawImage(drawn, 0, 0, canvas.width, canvas.height);
  return png(canvas);
}

/** A captured view (a canvas rendered at `scale` times its on-screen size) framed like the SVG, as a PNG at the
 * same scale. Runs in the browser. */
export async function framedPng(view: HTMLCanvasElement, text: FigureText, scale = 2): Promise<Blob> {
  const [w, h] = [view.width / scale, view.height / scale];
  const width = Math.max(w + 2 * MARGIN, 720);
  const frame = layout(text, width);
  const height = frame.top + h + frame.bottom;
  const x = (width - w) / 2;
  const drawn = await image(
    [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" font-family="${FONT}">`,
      `<rect width="100%" height="100%" fill="#ffffff"/>`,
      `<rect x="${x}" y="${frame.top}" width="${w}" height="${h}" rx="8" fill="${PLOT_BACKGROUND}"/>`,
      frameSvg(text, frame, frame.top + h),
      "</svg>",
    ].join(""),
  );
  const canvas = Object.assign(document.createElement("canvas"), { width: width * scale, height: height * scale });
  const context = canvas.getContext("2d")!;
  context.drawImage(drawn, 0, 0, canvas.width, canvas.height);
  context.drawImage(view, x * scale, frame.top * scale);
  return png(canvas);
}

/** Saves a file the browser holds, under a name. */
export function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
