import { ImageResponse } from "next/og";

import { getCounts } from "@/lib/data";

export const alt = "Axonarium: an open, cited map of how the brain and body are wired";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const revalidate = 3600;

// The link preview: the name, the promise and today's counts. Text only, so no atlas content is redistributed.
export default async function Image() {
  const counts = await getCounts();
  const stats = counts
    ? [
        ["claims", counts.claims],
        ["connections", counts.edges],
        ["species", counts.species],
      ]
    : [];
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: "radial-gradient(circle at 75% 60%, #1e2a4a 0%, #0b1020 60%)",
          color: "#f8fafc",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 40, fontWeight: 700 }}>
          <div style={{ width: 22, height: 22, borderRadius: 11, background: "#f97316" }} />
          <div style={{ width: 22, height: 22, borderRadius: 11, background: "#22d3ee", marginLeft: -12 }} />
          <div style={{ width: 22, height: 22, borderRadius: 11, background: "#a78bfa", marginLeft: -12 }} />
          <span style={{ marginLeft: 8 }}>Axonarium</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.05, maxWidth: 980 }}>
            An open, cited map of how the brain and body are wired.
          </div>
          <div style={{ fontSize: 30, color: "#cbd5e1", maxWidth: 960 }}>
            Every connection backed by cited claims, tagged by species and method. Starting with the amygdala.
          </div>
        </div>
        <div style={{ display: "flex", gap: 56, fontSize: 28, color: "#cbd5e1" }}>
          {stats.map(([label, value]) => (
            <div key={label} style={{ display: "flex", gap: 12, alignItems: "baseline" }}>
              <span style={{ fontSize: 44, fontWeight: 700, color: "#f8fafc" }}>{value.toLocaleString("en")}</span>
              <span>{label}</span>
            </div>
          ))}
          <span style={{ marginLeft: "auto", alignSelf: "flex-end" }}>axonarium.com</span>
        </div>
      </div>
    ),
    size,
  );
}
