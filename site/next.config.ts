import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The deploy's snapshot of the database (lib/data.ts, ADR 0017): bundled with every server route, never public.
  outputFileTracingIncludes: {
    "/**": ["./snapshot/snapshot.json"],
  },
};

export default nextConfig;
