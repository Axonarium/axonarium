// The URLs search engines are offered: the main pages, every connection and every connected atlas region.

import { edgeHref, regionHref } from "./format";
import type { Edge } from "./types";

export const SITE = "https://axonarium.com";

const PAGES = ["", "/brain", "/explore", "/atlases", "/about"];

export function sitemapUrls(edges: Pick<Edge, "id" | "subject_id" | "object_id">[], regions: Set<string>): string[] {
  const connected = new Set(edges.flatMap((e) => [e.subject_id, e.object_id]).filter((id) => regions.has(id)));
  return [
    ...PAGES.map((page) => `${SITE}${page}`),
    ...edges.map((e) => `${SITE}${edgeHref(e.id)}`),
    ...[...connected].sort().map((id) => `${SITE}${regionHref(id)}`),
  ];
}
