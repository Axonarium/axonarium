import type { MetadataRoute } from "next";

import { getRegionNames, listEdges } from "@/lib/data";
import { sitemapUrls } from "@/lib/sitemap";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const edges = (await listEdges()) ?? [];
  const regions = await getRegionNames([...new Set(edges.flatMap((e) => [e.subject_id, e.object_id]))]);
  return sitemapUrls(edges, new Set(Object.keys(regions))).map((url) => ({ url }));
}
