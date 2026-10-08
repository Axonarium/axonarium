// One page of each type, with IDs from the snapshot the build read, so every page shows real data.
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { edgeHref, regionHref, sourceHref } from "../lib/format";
import type { Tables } from "../lib/offline";

function snapshot(): Tables {
  try {
    return (JSON.parse(readFileSync(join(__dirname, "..", "snapshot", "snapshot.json"), "utf-8")) as { tables: Tables }).tables;
  } catch {
    throw new Error("No snapshot/snapshot.json: write one with `uv run python -m build --snapshot site/snapshot/snapshot.json`.");
  }
}

const tables = snapshot();
const claim = tables.connectivity_claims.find((c) => c.status === "accepted") ?? tables.connectivity_claims[0];
const region = tables.regions.find((r) => r.amygdala) ?? tables.regions[0];

export const PAGES: Record<string, string> = {
  home: "/",
  brain: "/brain",
  explore: "/explore",
  regions: "/regions",
  region: regionHref(region.id),
  claim: `/claims/${claim.id}`,
  connection: edgeHref(tables.edges[0].id),
  sources: "/sources",
  source: sourceHref(claim.source_key),
  atlases: "/atlases",
  about: "/about",
  "not found": "/claims/clm-0000000000",
};

export const CLAIM = claim.id;
